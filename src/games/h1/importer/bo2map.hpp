#pragma once

// Black Ops II -> H1 map importer. Reads the .h1map export of the CodLegacy tool (bo2_h1_export) and the
// files next to it, and writes the H1 map assets that buildzone reads to dump/<map>/. See docs/BO2_IMPORT.md.

namespace zonetool::h1::importer
{
	bool import_bo2_map(const std::filesystem::path& h1map_file, const std::string& name_override);
}
