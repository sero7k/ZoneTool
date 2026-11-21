#include <std_include.hpp>
#include "zonetool/t7/converter/h1/include.hpp"
#include "gfximage.hpp"

#include "zonetool/t7/assets/gfximage.hpp"

namespace zonetool::t7
{
	namespace converter::h1
	{
		namespace gfximage
		{
			void dump(GfxImage* asset)
			{
				// TODO: BO3 normal maps are BC5 (two channel) and gloss/spec live in separate
				//       images; H1 techsets expect different packing. Only colour maps are used
				//       by the material converter for now, so a plain dds is enough.
				zonetool::t7::gfx_image::dump_dds(asset);
			}
		}
	}
}
