#pragma once

namespace zonetool::t7
{
	// Offline reader for Black Ops 3 PC fastfiles (no game code involved).
	// Parses the XFile header, decompresses the block stream and reads the XAssetList
	// head (script strings + asset type table), which is enough to list how many assets
	// of each type a zone holds. Full asset loading still goes through the game
	// (BlackOps3_UnrankedDedicatedServer.exe, see zonetool.cpp) or through ACTS.
	namespace fastfile
	{
		struct asset_entry
		{
			std::int32_t type;
			std::uint64_t pointer;
		};

		struct zone_info
		{
			std::string name;
			std::uint32_t version{};
			std::uint8_t server{};
			std::uint8_t compression{};
			std::uint8_t platform{};
			std::uint8_t encrypted{};
			std::string builder;
			std::uint64_t size{};
			std::uint64_t external_size{};
			std::uint64_t block_sizes[10]{};

			std::vector<std::uint8_t> data; // decompressed zone
			std::vector<std::string> strings;
			std::vector<asset_entry> assets;
		};

		// throws std::runtime_error on failure
		zone_info read(const std::string& path, bool read_asset_list = true);

		// resolves "<name>", "zone/<name>.ff", "../zone/<name>.ff"
		std::string resolve_path(const std::string& zone);

		// prints the header, the asset type summary and optionally writes dump/<name>.zone
		void print_info(const std::string& zone, bool dump_decompressed);
	}
}
