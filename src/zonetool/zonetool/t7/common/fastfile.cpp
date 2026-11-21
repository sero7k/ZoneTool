#include <std_include.hpp>
#include "zonetool/t7/zonetool.hpp"
#include "fastfile.hpp"

#include <zlib.h>
#include <lz4.h>

// Black Ops 3 PC fastfile layout (written from the format, see docs/bo3-support.md):
//
//   XFileHeader (0x248 bytes, "TAff0000", version 0x251 retail / 0x1FB beta)
//   then a sequence of stream blocks:
//     DBStreamHeader { u32 compressedSize; u32 uncompressedSize; u32 alignedSize; u32 offset; }
//     alignedSize bytes of data (first compressedSize bytes are the compressed payload)
//   "offset" is the file offset of the DBStreamHeader itself (used as a sanity check).
//   A header with uncompressedSize == 0 marks padding up to the next 0x800000 boundary.
//
// The decompressed stream starts with XAssetList (0x30 bytes) in the VIRTUAL block.

namespace zonetool::t7
{
	namespace fastfile
	{
		namespace
		{
#pragma pack(push, 1)
			struct XFileHeader
			{
				char magic[8];
				std::uint32_t version;
				std::uint8_t server;
				std::uint8_t compression;
				std::uint8_t platform;
				std::uint8_t encrypted;
				std::uint64_t timestamp;
				std::uint32_t changelist;
				std::uint32_t archiveChecksum[4];
				char builder[32];
				std::uint32_t metaVersion;
				char mergeFastfile[64];
				std::uint64_t size;
				std::uint64_t externalSize;
				std::uint64_t memMappedOffset;
				std::uint64_t blockSize[10];
				char fastfileName[64];
				std::uint8_t signature[256];
				std::uint8_t aesIV[16];
			};

			struct DBStreamHeader
			{
				std::uint32_t compressedSize;
				std::uint32_t uncompressedSize;
				std::uint32_t alignedSize;
				std::uint32_t offset;
			};

			struct XAssetListHead
			{
				std::int32_t stringsCount;
				std::int32_t pad04;
				std::uint64_t strings;
				std::uint32_t unk10;
				std::int32_t pad14;
				std::uint64_t unk18;
				std::int32_t assetCount;
				std::int32_t pad24;
				std::uint64_t assets;
			};
#pragma pack(pop)

			static_assert(sizeof(XFileHeader) == 0x248);
			static_assert(sizeof(DBStreamHeader) == 0x10);
			static_assert(sizeof(XAssetListHead) == 0x30);

			constexpr std::uint64_t FOLLOWING = 0xFFFFFFFFFFFFFFFFull; // -1: data follows in the stream
			constexpr std::uint64_t INSERT = 0xFFFFFFFFFFFFFFFEull;    // -2: data follows, pointer stored for reuse

			const char* compression_name(const std::uint8_t c)
			{
				switch (c)
				{
				case 0: return "none";
				case 1: return "zlib";
				case 2: return "zlib_hc";
				case 3: return "lz4";
				case 4: return "lz4_hc";
				case 5: return "bdelta_uncomp";
				case 6: return "bdelta_zlib";
				default: return "unknown";
				}
			}

			const char* platform_name(const std::uint8_t p)
			{
				switch (p)
				{
				case 0: return "pc";
				case 1: return "xbox";
				case 2: return "playstation";
				case 3: return "dev";
				default: return "unknown";
				}
			}

			std::string fixed_string(const char* str, const size_t max)
			{
				return std::string(str, strnlen(str, max));
			}

			void decompress_block(const std::uint8_t compression, const std::uint8_t* in, const size_t in_size,
				std::uint8_t* out, const size_t out_size)
			{
				switch (compression)
				{
				case 0:
					if (in_size < out_size)
					{
						throw std::runtime_error("uncompressed block is too small");
					}
					std::memcpy(out, in, out_size);
					return;
				case 1:
				case 2:
				{
					auto dest_len = static_cast<uLongf>(out_size);
					const auto result = uncompress(out, &dest_len, in, static_cast<uLong>(in_size));
					if (result != Z_OK || dest_len != out_size)
					{
						throw std::runtime_error(utils::string::va("zlib error %d (0x%lX/0x%llX)", result,
							static_cast<unsigned long>(dest_len), static_cast<unsigned long long>(out_size)));
					}
					return;
				}
				case 3:
				case 4:
				{
					const auto result = LZ4_decompress_safe(reinterpret_cast<const char*>(in), reinterpret_cast<char*>(out),
						static_cast<int>(in_size), static_cast<int>(out_size));
					if (result < 0 || static_cast<size_t>(result) != out_size)
					{
						throw std::runtime_error(utils::string::va("lz4 error %d", result));
					}
					return;
				}
				default:
					throw std::runtime_error(utils::string::va("unsupported compression %d (%s)", compression, compression_name(compression)));
				}
			}

			class stream_reader
			{
			public:
				explicit stream_reader(const std::vector<std::uint8_t>& data) : data_(data) {}

				template <typename T> T read()
				{
					T value{};
					this->read(&value, sizeof(T));
					return value;
				}

				void read(void* out, const size_t size)
				{
					if (this->pos_ + size > this->data_.size())
					{
						throw std::runtime_error(utils::string::va("read past end of zone (0x%llX + 0x%llX)",
							static_cast<unsigned long long>(this->pos_), static_cast<unsigned long long>(size)));
					}
					std::memcpy(out, this->data_.data() + this->pos_, size);
					this->pos_ += size;
				}

				std::string read_string()
				{
					std::string str;
					while (true)
					{
						const auto c = this->read<char>();
						if (!c)
						{
							break;
						}
						str.push_back(c);
					}
					return str;
				}

				void align(const size_t alignment)
				{
					this->pos_ = (this->pos_ + alignment - 1) & ~(alignment - 1);
				}

				size_t pos() const
				{
					return this->pos_;
				}

			private:
				const std::vector<std::uint8_t>& data_;
				size_t pos_{};
			};

			void read_asset_list(zone_info& info)
			{
				stream_reader reader(info.data);
				const auto head = reader.read<XAssetListHead>();

				if (head.stringsCount < 0 || head.assetCount < 0 || head.assetCount > 0x100000)
				{
					throw std::runtime_error("invalid XAssetList");
				}

				// script strings: pointer array, then each string inline
				if (head.strings == FOLLOWING || head.strings == INSERT)
				{
					reader.align(8);
					std::vector<std::uint64_t> pointers(static_cast<size_t>(head.stringsCount));
					if (!pointers.empty())
					{
						reader.read(pointers.data(), pointers.size() * sizeof(std::uint64_t));
					}

					for (const auto ptr : pointers)
					{
						if (ptr == FOLLOWING || ptr == INSERT)
						{
							info.strings.emplace_back(reader.read_string());
						}
						else
						{
							info.strings.emplace_back();
						}
					}
				}

				if (head.unk18)
				{
					// never seen set in retail zones (ACTS throws on it as well)
					ZONETOOL_WARNING("XAssetList.unk18 is set, asset table offset may be wrong");
				}

				if (head.assets == FOLLOWING || head.assets == INSERT)
				{
					reader.align(8);
					for (auto i = 0; i < head.assetCount; i++)
					{
						asset_entry entry{};
						entry.type = reader.read<std::int32_t>();
						reader.read<std::int32_t>(); // padding
						entry.pointer = reader.read<std::uint64_t>();
						info.assets.emplace_back(entry);
					}
				}
			}
		}

		std::string resolve_path(const std::string& zone)
		{
			const auto ff = zone.ends_with(".ff") ? zone : zone + ".ff";
			for (const auto& candidate : { zone, ff, "zone/"s + ff, "../zone/"s + ff })
			{
				if (std::filesystem::is_regular_file(candidate))
				{
					return candidate;
				}
			}
			return {};
		}

		zone_info read(const std::string& path, const bool read_assets)
		{
			std::ifstream file(path, std::ios::binary);
			if (!file.is_open())
			{
				throw std::runtime_error("can't open " + path);
			}

			const std::vector<std::uint8_t> buffer((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
			if (buffer.size() < sizeof(XFileHeader))
			{
				throw std::runtime_error("file too small for a BO3 fastfile header");
			}

			XFileHeader header{};
			std::memcpy(&header, buffer.data(), sizeof(header));

			if (std::memcmp(header.magic, "TAff0000", 8) != 0)
			{
				throw std::runtime_error("bad magic (not a Treyarch T7 fastfile)");
			}

			if (header.version != 0x251 && header.version != 0x1FB)
			{
				throw std::runtime_error(utils::string::va("unsupported fastfile version 0x%X (expected 0x251)", header.version));
			}

			zone_info info{};
			info.name = fixed_string(header.fastfileName, sizeof(header.fastfileName));
			info.version = header.version;
			info.server = header.server;
			info.compression = header.compression;
			info.platform = header.platform;
			info.encrypted = header.encrypted;
			info.builder = fixed_string(header.builder, sizeof(header.builder));
			info.size = header.size;
			info.external_size = header.externalSize;
			std::memcpy(info.block_sizes, header.blockSize, sizeof(info.block_sizes));

			if (header.encrypted)
			{
				// AES-CTR with a per-fastfile key; keys are not distributed with ZoneTool
				throw std::runtime_error("encrypted fastfiles are not supported, use the ACTS bridge (zonetool -dumpzone bo3 ...)");
			}

			if (header.size > 0x100000000ull)
			{
				throw std::runtime_error("zone size is too large");
			}

			info.data.resize(static_cast<size_t>(header.size));

			size_t pos = sizeof(XFileHeader);
			size_t out = 0;
			while (out < info.data.size() && pos + sizeof(DBStreamHeader) <= buffer.size())
			{
				DBStreamHeader block{};
				std::memcpy(&block, buffer.data() + pos, sizeof(block));

				if (block.offset != pos)
				{
					throw std::runtime_error(utils::string::va("bad block position 0x%X != 0x%llX", block.offset, static_cast<unsigned long long>(pos)));
				}

				if (!block.uncompressedSize)
				{
					// padding marker: skip to the next 8MB boundary after this header
					pos = (pos + sizeof(DBStreamHeader) + 0x7FFFFF) & ~static_cast<size_t>(0x7FFFFF);
					continue;
				}

				pos += sizeof(DBStreamHeader);
				if (pos + block.alignedSize > buffer.size() || block.compressedSize > block.alignedSize ||
					out + block.uncompressedSize > info.data.size())
				{
					throw std::runtime_error(utils::string::va("block at 0x%llX is out of bounds", static_cast<unsigned long long>(pos)));
				}

				decompress_block(header.compression, buffer.data() + pos, block.compressedSize, info.data.data() + out, block.uncompressedSize);

				out += block.uncompressedSize;
				pos += block.alignedSize;
			}

			if (out != info.data.size())
			{
				ZONETOOL_WARNING("Decompressed 0x%llX of 0x%llX bytes", static_cast<unsigned long long>(out), static_cast<unsigned long long>(info.data.size()));
				info.data.resize(out);
			}

			if (read_assets)
			{
				read_asset_list(info);
			}

			return info;
		}

		void print_info(const std::string& zone, const bool dump_decompressed)
		{
			const auto path = resolve_path(zone);
			if (path.empty())
			{
				ZONETOOL_ERROR("Fastfile \"%s\" not found", zone.data());
				return;
			}

			try
			{
				const auto info = read(path);

				ZONETOOL_INFO("%s: \"%s\" version 0x%X, %s, %s, compression %s, builder \"%s\"",
					path.data(), info.name.data(), info.version, info.server ? "server" : "client",
					platform_name(info.platform), compression_name(info.compression), info.builder.data());
				ZONETOOL_INFO("size 0x%llX, external size 0x%llX", static_cast<unsigned long long>(info.size),
					static_cast<unsigned long long>(info.external_size));

				static const char* block_names[] = { "temp", "runtime_virtual", "runtime_physical", "delay_virtual",
					"delay_physical", "virtual", "physical", "streamer_reserve", "streamer", "memmapped" };
				for (auto i = 0; i < 10; i++)
				{
					if (info.block_sizes[i])
					{
						ZONETOOL_INFO("  block %-16s 0x%llX", block_names[i], static_cast<unsigned long long>(info.block_sizes[i]));
					}
				}

				ZONETOOL_INFO("%zu script string(s), %zu asset(s)", info.strings.size(), info.assets.size());

				std::map<std::int32_t, size_t> counts;
				for (const auto& asset : info.assets)
				{
					counts[asset.type]++;
				}

				for (const auto& [type, count] : counts)
				{
					const auto* name = (type >= 0 && type < ASSET_TYPE_COUNT) ? type_to_string(static_cast<XAssetType>(type)) : "unknown";
					ZONETOOL_INFO("  %-28s %zu", name, count);
				}

				if (dump_decompressed)
				{
					std::filesystem::create_directories("dump");
					const auto out_path = "dump/"s + (info.name.empty() ? std::filesystem::path(path).stem().string() : info.name) + ".zone";
					std::ofstream out(out_path, std::ios::binary);
					out.write(reinterpret_cast<const char*>(info.data.data()), static_cast<std::streamsize>(info.data.size()));
					ZONETOOL_INFO("Decompressed zone written to %s", out_path.data());
				}
			}
			catch (const std::exception& e)
			{
				ZONETOOL_ERROR("ffinfo \"%s\": %s", path.data(), e.what());
			}
		}
	}
}
