#pragma once

namespace zonetool::t7
{
	namespace converter::h1
	{
		namespace material
		{
			// queues the material; the json is written by flush() once the whole zone has been
			// seen, because the H1 techset depends on whether an xmodel uses the material
			void dump(Material* asset);

			// remember materials used by xmodels (they need H1 model techsets, not world ones)
			void note_model_materials(XModel* asset);

			// write materials\<name>.json for every queued material, then clear the queue
			void flush();
		}
	}
}
