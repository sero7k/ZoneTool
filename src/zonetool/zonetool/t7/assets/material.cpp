#include <std_include.hpp>
#include "zonetool/t7/zonetool.hpp"
#include "material.hpp"

namespace zonetool::t7
{
	namespace material
	{
		std::string clean_name(const std::string& name)
		{
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

		void dump(Material* asset)
		{
			if (!asset || !asset->info.name)
			{
				return;
			}

			ordered_json data;
			data["name"] = asset->info.name;
			data["techniqueSet"] = (asset->techniqueSet && asset->techniqueSet->name) ? asset->techniqueSet->name : "";
			data["gameFlags"] = asset->info.gameFlags;
			data["layerSortDecal"] = asset->info.layerSortDecal;
			data["textureAtlasRowCount"] = asset->info.textureAtlasRowCount;
			data["textureAtlasColumnCount"] = asset->info.textureAtlasColumnCount;
			data["drawSurf"] = asset->info.drawSurf.packed;
			data["surfaceTypeBits"] = asset->info.surfaceTypeBits;
			data["layeredSurfaceTypes"] = asset->info.layeredSurfaceTypes;
			data["surfaceFlags"] = asset->info.surfaceFlags;
			data["contents"] = asset->info.contents;
			data["cameraRegion"] = static_cast<int>(asset->cameraRegion);

			ordered_json textures = json::array();
			for (auto i = 0; i < asset->textureCount && asset->textureTable; i++)
			{
				const auto& tex = asset->textureTable[i];
				ordered_json t;
				t["image"] = (tex.image && tex.image->name) ? tex.image->name : "";
				t["imageSemantic"] = tex.image ? static_cast<int>(tex.image->semantic) : -1;
				t["nameHash"] = tex.nameHash;
				t["uvScale"] = { tex.uvScale[0], tex.uvScale[1] };
				t["usage"] = tex.usage;
				t["isMatureContent"] = tex.isMatureContent;
				textures.push_back(t);
			}
			data["textureTable"] = textures;

			ordered_json constants = json::array();
			for (auto i = 0; i < asset->constantCount && asset->constantTable; i++)
			{
				const auto& c = asset->constantTable[i];
				ordered_json e;
				e["name"] = std::string(c.name, strnlen(c.name, sizeof(c.name)));
				e["nameHash"] = c.nameHash;
				e["literal"] = { c.literal[0], c.literal[1], c.literal[2], c.literal[3] };
				constants.push_back(e);
			}
			data["constantTable"] = constants;

			ordered_json samplers = json::array();
			for (auto i = 0; i < asset->samplerCount && asset->samplerTable; i++)
			{
				samplers.push_back(asset->samplerTable[i].nameHash);
			}
			data["samplerTable"] = samplers;

			data["enemyMaterial"] = (asset->enemyMaterial && asset->enemyMaterial->info.name) ? asset->enemyMaterial->info.name : "";

			const auto path = "materials\\"s + clean_name(asset->info.name) + ".t7material.json"s;
			auto file = filesystem::file(path);
			file.open("wb");
			file.write(data.dump(4, ' ', true, nlohmann::detail::error_handler_t::replace));
			file.close();
		}
	}
}
