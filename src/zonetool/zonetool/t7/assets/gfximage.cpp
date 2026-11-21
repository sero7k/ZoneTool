#include <std_include.hpp>
#include "zonetool/t7/zonetool.hpp"
#include "gfximage.hpp"

#include "zonetool/t7/common/xpak.hpp"

#pragma warning( push )
#pragma warning( disable : 4459 )
#include <DirectXTex.h>
#pragma warning( pop )

namespace zonetool::t7
{
	namespace gfx_image
	{
		namespace
		{
			struct image_layout
			{
				DXGI_FORMAT format;
				std::uint32_t width;
				std::uint32_t height;
				std::uint32_t depth;     // 3d textures only
				std::uint32_t elements;  // array size * faces
				std::uint32_t levels;
				bool cube;
				DirectX::TEX_DIMENSION dimension;
			};

			size_t level_size(DXGI_FORMAT format, std::uint32_t width, std::uint32_t height, std::uint32_t depth)
			{
				size_t row_pitch{};
				size_t slice_pitch{};
				if (FAILED(DirectX::ComputePitch(format, width, height, row_pitch, slice_pitch)))
				{
					return 0;
				}
				return slice_pitch * std::max(1u, depth);
			}

			// total bytes for "levels" mips of every element, D3D order: element -> mip
			size_t total_size(const image_layout& layout, std::uint32_t levels)
			{
				size_t size = 0;
				for (auto l = 0u; l < levels; l++)
				{
					size += level_size(layout.format,
						std::max(1u, layout.width >> l),
						std::max(1u, layout.height >> l),
						std::max(1u, layout.depth >> l));
				}
				return size * layout.elements;
			}

			bool write_dds(const std::string& name, image_layout layout, const std::uint8_t* data, size_t data_size)
			{
				if (!data || !data_size || !layout.width || !layout.height)
				{
					return false;
				}

				// drop mips we do not have data for (some parts only carry the top levels)
				while (layout.levels > 1 && total_size(layout, layout.levels) > data_size)
				{
					layout.levels--;
				}

				if (total_size(layout, layout.levels) > data_size)
				{
					ZONETOOL_WARNING("Image \"%s\": not enough pixel data (0x%llX < 0x%llX), format %d %ux%u",
						name.data(), static_cast<unsigned long long>(data_size),
						static_cast<unsigned long long>(total_size(layout, layout.levels)),
						static_cast<int>(layout.format), layout.width, layout.height);
					return false;
				}

				std::vector<DirectX::Image> images;
				auto* ptr = data;
				for (auto e = 0u; e < layout.elements; e++)
				{
					for (auto l = 0u; l < layout.levels; l++)
					{
						DirectX::Image img{};
						img.width = std::max(1u, layout.width >> l);
						img.height = std::max(1u, layout.height >> l);
						img.format = layout.format;
						DirectX::ComputePitch(img.format, img.width, img.height, img.rowPitch, img.slicePitch);
						img.pixels = const_cast<std::uint8_t*>(ptr);
						images.push_back(img);

						ptr += img.slicePitch * std::max(1u, layout.depth >> l);
					}
				}

				DirectX::TexMetadata meta{};
				meta.width = layout.width;
				meta.height = layout.height;
				meta.depth = std::max(1u, layout.depth);
				meta.arraySize = layout.elements;
				meta.mipLevels = layout.levels;
				meta.format = layout.format;
				meta.dimension = layout.dimension;
				if (layout.cube)
				{
					meta.miscFlags |= DirectX::TEX_MISC_TEXTURECUBE;
				}

				const auto parent_path = filesystem::get_dump_path() + "images\\";
				const auto spath = parent_path + clean_name(name) + ".dds";
				const std::wstring wpath(spath.begin(), spath.end());

				std::filesystem::create_directories(parent_path);

				const auto result = DirectX::SaveToDDSFile(images.data(), images.size(), meta, DirectX::DDS_FLAGS_NONE, wpath.data());
				if (FAILED(result))
				{
					ZONETOOL_WARNING("Failed to write image \"%s\"", spath.data());
					return false;
				}

				return true;
			}

			image_layout get_layout(GfxImage* asset, std::uint32_t width, std::uint32_t height, std::uint32_t levels)
			{
				image_layout layout{};
				layout.format = asset->format;
				layout.width = width;
				layout.height = height;
				layout.depth = 1;
				layout.elements = 1;
				layout.levels = std::max(1u, levels);
				layout.dimension = DirectX::TEX_DIMENSION_TEXTURE2D;

				switch (asset->mapType)
				{
				case MAPTYPE_CUBE:
					layout.cube = true;
					layout.elements = 6;
					break;
				case MAPTYPE_CUBE_ARRAY:
					// UNVERIFIED: assumes depth holds the cube count
					layout.cube = true;
					layout.elements = 6u * std::max<std::uint32_t>(1u, asset->depth);
					break;
				case MAPTYPE_2D_ARRAY:
					// UNVERIFIED: assumes depth holds the array size
					layout.elements = std::max<std::uint32_t>(1u, asset->depth);
					break;
				case MAPTYPE_3D:
					layout.depth = std::max<std::uint32_t>(1u, asset->depth);
					layout.dimension = DirectX::TEX_DIMENSION_TEXTURE3D;
					break;
				default:
					break;
				}

				return layout;
			}
		}

		std::string clean_name(const std::string& name)
		{
			// same rule as zonetool::h1 so the H1 linker finds images\<name>.dds
			auto new_name = name;
			for (auto& c : new_name)
			{
				if (c == '*')
				{
					c = '_';
				}
			}
			return new_name;
		}

		bool dump_dds(GfxImage* asset)
		{
			if (!asset || !asset->name)
			{
				return false;
			}

			// loaded image: pixels live in the zone
			if (asset->pixels && asset->totalSize && !asset->streamedPartCount)
			{
				const auto layout = get_layout(asset, asset->width, asset->height, asset->levelCount);
				return write_dds(asset->name, layout, asset->pixels, asset->totalSize);
			}

			// streamed image: pick the highest resolution part available in the xpaks
			std::vector<int> order;
			for (auto i = 0; i < std::min<int>(asset->streamedPartCount, 4); i++)
			{
				order.push_back(i);
			}

			std::sort(order.begin(), order.end(), [&](const int a, const int b)
			{
				const auto& pa = asset->streamedParts[a];
				const auto& pb = asset->streamedParts[b];
				return static_cast<std::uint32_t>(pa.width) * pa.height > static_cast<std::uint32_t>(pb.width) * pb.height;
			});

			for (const auto index : order)
			{
				const auto& part = asset->streamedParts[index];
				if (!part.xpakEntry.key || !part.levelCountAndSize.pixelSize)
				{
					continue;
				}

				const auto data = xpak::get_data_for_xpak_key(part.xpakEntry.key, part.levelCountAndSize.pixelSize);
				if (data.empty())
				{
					continue;
				}

				const auto layout = get_layout(asset, part.width, part.height, part.levelCountAndSize.levelCount);
				if (write_dds(asset->name, layout, data.data(), data.size()))
				{
					return true;
				}
			}

			// fallback: low-res pixels that may still be resident
			if (asset->pixels && asset->totalSize)
			{
				const auto layout = get_layout(asset, asset->width, asset->height, asset->levelCount);
				if (write_dds(asset->name, layout, asset->pixels, asset->totalSize))
				{
					ZONETOOL_WARNING("Image \"%s\": streamed data not found in xpak, dumped resident pixels instead", asset->name);
					return true;
				}
			}

			ZONETOOL_WARNING("Image \"%s\": no pixel data found (parts %u, xpak missing?)", asset->name, asset->streamedPartCount);
			return false;
		}

		void dump(GfxImage* asset)
		{
			dump_dds(asset);

			ordered_json data;
			data["name"] = asset->name;
			data["semantic"] = static_cast<int>(asset->semantic);
			data["mapType"] = static_cast<int>(asset->mapType);
			data["category"] = static_cast<int>(asset->category);
			data["flags"] = asset->flags;
			data["format"] = static_cast<int>(asset->format);
			data["width"] = asset->width;
			data["height"] = asset->height;
			data["depth"] = asset->depth;
			data["levelCount"] = asset->levelCount;
			data["totalSize"] = asset->totalSize;
			data["streamedPartCount"] = asset->streamedPartCount;
			ordered_json parts = json::array();
			for (auto i = 0; i < std::min<int>(asset->streamedPartCount, 4); i++)
			{
				const auto& part = asset->streamedParts[i];
				ordered_json p;
				p["width"] = part.width;
				p["height"] = part.height;
				p["levelCount"] = part.levelCountAndSize.levelCount;
				p["pixelSize"] = part.levelCountAndSize.pixelSize;
				p["xpakKey"] = utils::string::va("%016llX", static_cast<unsigned long long>(part.xpakEntry.key));
				parts.push_back(p);
			}
			data["streamedParts"] = parts;

			const auto path = "images\\"s + clean_name(asset->name) + ".t7image.json"s;
			auto file = filesystem::file(path);
			file.open("wb");
			file.write(data.dump(4, ' ', true, nlohmann::detail::error_handler_t::replace));
			file.close();
		}
	}
}
