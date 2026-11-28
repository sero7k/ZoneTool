#pragma once

namespace zonetool::iw7
{
	namespace converter::h1
	{
		namespace material
		{
			void dump(zonetool::iw7::Material* asset);
			void dump_used(const zonetool::iw7::Material* asset);
			bool is_layered(const zonetool::iw7::Material* asset);
			bool draws_layer_blend(const zonetool::iw7::Material* asset);
		}
	}
}
