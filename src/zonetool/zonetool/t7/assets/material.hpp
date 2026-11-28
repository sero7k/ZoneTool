#pragma once

namespace zonetool::t7
{
	namespace material
	{
		std::string clean_name(const std::string& name);

		// native t7 dump: "<dump>/materials/<name>.t7material.json" with the raw BO3 fields
		void dump(Material* asset);
	}
}
