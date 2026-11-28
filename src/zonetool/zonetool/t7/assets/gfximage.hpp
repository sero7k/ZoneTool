#pragma once

namespace zonetool::t7
{
	namespace gfx_image
	{
		std::string clean_name(const std::string& name);

		// writes "<dump>/images/<clean name>.dds", using the loaded pixels or the
		// highest resolution streamed part found in the zone's .xpak files
		bool dump_dds(GfxImage* asset);

		// native t7 dump (dds + small json with the image header)
		void dump(GfxImage* asset);
	}
}
