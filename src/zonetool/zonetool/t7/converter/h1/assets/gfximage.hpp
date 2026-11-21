#pragma once

namespace zonetool::t7
{
	namespace converter::h1
	{
		namespace gfximage
		{
			// BO3 -> H1: writes images\<name>.dds, which the H1 linker loads directly
			// (zonetool::h1 directxtex::load_image), so no .h1Image is needed
			void dump(GfxImage* asset);
		}
	}
}
