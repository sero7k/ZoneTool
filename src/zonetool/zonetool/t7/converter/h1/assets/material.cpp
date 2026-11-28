#include <std_include.hpp>
#include "zonetool/t7/converter/h1/include.hpp"
#include "material.hpp"

namespace zonetool::t7
{
	namespace converter::h1
	{
		namespace material
		{
			// BO3 -> H1 material conversion.
			//
			// BO3 uses its own (hashed) shader/techset system, which cannot be translated to H1
			// techsets 1:1. Like the iw7 -> h1 path, each material is remapped onto a small set of
			// Ghosts (_iw6) techsets that the H1/HMW mod already ships, keeping one colour map:
			//
			//   world opaque   wc_l_sm_ndw_b0c0l0_nfwpf_iw6
			//   world blended  wc_l_sm_ndw_b0c0l0_cltrans_iw6
			//   model opaque   mc_l_sm_r0c0n0s0l0_nfwpf_iw6
			//   model blended  mc_l_t0c0n0s0l0_nfwpf_iw6
			//   emissive/add   effect_add_lin_ct_nofog_ndw_bl_blmod_iw6
			//   sky            wc_sky_bl_iw6
			//
			// TODO: normal/spec/gloss maps, detail maps, BO3 "_atest" detection by techset hash,
			//       sortKey values checked in game (the values below are the ones the iw7 port uses).

			namespace
			{
				std::vector<Material*> queued;
				std::unordered_set<Material*> queued_set;
				std::unordered_set<std::string> model_materials;

				constexpr std::uint32_t HASH_COLOR_MAP = 2695565377u;
				constexpr std::uint32_t HASH_NORMAL_MAP = 1507003663u;
				constexpr std::uint32_t HASH_SPECULAR_MAP = 887934131u;

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

				bool ends_with(const std::string& str, const char* suffix)
				{
					const auto len = strlen(suffix);
					return str.size() > len && str.compare(str.size() - len, len, suffix) == 0;
				}

				// higher is more likely to be the colour (albedo) map
				int score_image(const MaterialTextureDef& tex)
				{
					if (!tex.image || !tex.image->name)
					{
						return -1000;
					}

					const std::string n = tex.image->name;

					switch (tex.image->semantic)
					{
					case IMG_SEMANTIC_DIFFUSE_MAP:
						return 20;
					case IMG_SEMANTIC_NORMAL_MAP:
					case IMG_SEMANTIC_SPECULAR_MASK:
					case IMG_SEMANTIC_SPECULAR_MAP:
					case IMG_SEMANTIC_GLOSS_MAP:
					case IMG_SEMANTIC_OCCLUSION_MAP:
					case IMG_SEMANTIC_REVEAL_MAP:
					case IMG_SEMANTIC_MULTIPLE_MASK:
					case IMG_SEMANTIC_THICKNESS_MAP:
					case IMG_SEMANTIC_ONE_CHANNEL:
					case IMG_SEMANTIC_TWO_CHANNEL:
					case IMG_SEMANTIC_LUT_TPAGE:
						return -50;
					default:
						break;
					}

					// BO3 naming: _c colour, _n normal, _g gloss, _s spec, _o occlusion, _r reveal
					if (ends_with(n, "_c") || ends_with(n, "_col") || ends_with(n, "_albedo"))
					{
						return 10;
					}
					if (ends_with(n, "_n") || ends_with(n, "_nml") || ends_with(n, "_g") || ends_with(n, "_s") ||
						ends_with(n, "_o") || ends_with(n, "_r") || ends_with(n, "_m") || n.find("_detail") != std::string::npos)
					{
						return -50;
					}

					return tex.image->semantic == IMG_SEMANTIC_2D ? 2 : 1;
				}

				std::string pick_color_map(Material* asset)
				{
					std::string best_name = "blank";
					int best = -100;
					for (auto i = 0; i < asset->textureCount && asset->textureTable; i++)
					{
						const auto score = score_image(asset->textureTable[i]);
						if (score > best)
						{
							best = score;
							best_name = asset->textureTable[i].image->name;
						}
					}

					if (best <= -50)
					{
						return "blank";
					}

					return best_name;
				}

				ordered_json make_constant(const char* name, std::uint32_t hash, float a, float b, float c, float d)
				{
					ordered_json e;
					e["name"] = name;
					e["nameHash"] = hash;
					e["literal"] = { a, b, c, d };
					return e;
				}

				ordered_json make_image(const std::string& image, int semantic, int sampler, int first, int last, std::uint32_t hash)
				{
					ordered_json e;
					e["image"] = image;
					e["semantic"] = semantic;
					e["samplerState"] = sampler;
					e["lastCharacter"] = last;
					e["firstCharacter"] = first;
					e["typeHash"] = hash;
					return e;
				}

				void write_json(Material* asset, const bool is_model)
				{
					const std::string name = asset->info.name;
					const std::string techset = (asset->techniqueSet && asset->techniqueSet->name) ? asset->techniqueSet->name : "";
					const auto color = pick_color_map(asset);

					const auto region = asset->cameraRegion;
					const bool is_sky = name.find("sky") != std::string::npos && (name.find("/sky") != std::string::npos || name.rfind("sky", 0) == 0 || name.find("_sky_") != std::string::npos);
					const bool is_decal = region == CAMERA_REGION_GBUFFER_DECAL || region == CAMERA_REGION_GBUFFER_DEPTH_HACK_DECAL;
					const bool is_trans = region == CAMERA_REGION_LIT_TRANS || region == CAMERA_REGION_LIT_TRANS_POST_RESOLVE ||
						region == CAMERA_REGION_DEPTH_HACK_TRANS || region == CAMERA_REGION_OIT;
					const bool is_emissive = region == CAMERA_REGION_EMISSIVE_FX;
					const bool alpha_tested = techset.find("atest") != std::string::npos || techset.find("alphatest") != std::string::npos;
					const bool blended = is_decal || is_trans || alpha_tested;

					ordered_json matdata;
					matdata["name"] = name;
					matdata["techniqueSet->og_name"] = techset;
					matdata["gameFlags"] = 0;
					matdata["sortKey"] = 2;
					matdata["renderFlags"] = 0;
					matdata["textureAtlasRowCount"] = asset->info.textureAtlasRowCount;
					matdata["textureAtlasColumnCount"] = asset->info.textureAtlasColumnCount;
					matdata["textureAtlasFrameBlend"] = 0;
					matdata["textureAtlasAsArray"] = 0;
					// TODO: BO3 surfaceTypeBits use a different surface type table than H1
					matdata["surfaceTypeBits"] = 0;
					matdata["stateFlags"] = 0;
					matdata["cameraRegion"] = 0;
					matdata["materialType"] = 0;
					matdata["assetFlags"] = zonetool::h1::MTL_ASSETFLAG_NONE;

					ordered_json constants = json::array();
					ordered_json images = json::array();

					if (is_sky)
					{
						matdata["techniqueSet->name"] = "wc_sky_bl_iw6";
						matdata["gameFlags"] = 12;
						matdata["sortKey"] = 3;
						matdata["materialType"] = 36;
						constants.push_back(make_constant("bloomParams", 3733414975u, 1.02f, 0.0f, 0.0f, 0.0f));
						images.push_back(make_image(color, 2, 243, 'c', 'p', HASH_COLOR_MAP));
					}
					else if (is_emissive)
					{
						matdata["techniqueSet->name"] = is_model ? "mc_unlit_blend_lin_ct_ndw_bl_abl_cltrans_iw6" : "effect_add_lin_ct_nofog_ndw_bl_blmod_iw6";
						matdata["gameFlags"] = is_model ? 0 : 8;
						matdata["sortKey"] = is_model ? 31 : 53;
						matdata["cameraRegion"] = is_model ? 3 : 4;
						matdata["materialType"] = is_model ? 3 : 0;
						constants.push_back(make_constant("textureAtlas", 1128936273u, 1.0f, 1.0f, 1.0f, 1.0f));
						constants.push_back(make_constant("colorTint", 3054254906u, 1.5f, 1.5f, 1.5f, 1.0f));
						constants.push_back(make_constant("bloomParams", 3733414975u, 1.0f, 0.0f, 0.0f, 0.0f));
						images.push_back(make_image(color, 2, is_model ? 19 : 243, 'c', 'p', HASH_COLOR_MAP));
					}
					else if (is_model)
					{
						matdata["techniqueSet->name"] = blended ? "mc_l_t0c0n0s0l0_nfwpf_iw6" : "mc_l_sm_r0c0n0s0l0_nfwpf_iw6";
						matdata["sortKey"] = blended ? 7 : 2;
						matdata["materialType"] = 3;
						constants.push_back(make_constant("envMapParms", 1033475292u, 0.0f, 1.0f, 2.0f, 2.0f));
						constants.push_back(make_constant("colorTint", 3054254906u, 1.0f, 1.0f, 1.0f, 1.0f));
						constants.push_back(make_constant("reflectionRa", 3344177073u, 8096.0f, 0.0f, 0.0f, 0.0f));
						constants.push_back(make_constant("bloomParams", 3733414975u, 1.0f, 0.0f, 0.0f, 0.0f));
						images.push_back(make_image("$black", 8, 19, 's', 'p', HASH_SPECULAR_MAP));
						images.push_back(make_image("$identitynormalmap", 5, 19, 'n', 'p', HASH_NORMAL_MAP));
						images.push_back(make_image(color, 2, 19, 'c', 'p', HASH_COLOR_MAP));
					}
					else
					{
						matdata["techniqueSet->name"] = blended ? "wc_l_sm_ndw_b0c0l0_cltrans_iw6" : "wc_l_sm_ndw_b0c0l0_nfwpf_iw6";
						matdata["sortKey"] = is_trans ? 24 : (blended ? 7 : 2);
						matdata["cameraRegion"] = blended ? 3 : 0;
						if (blended)
						{
							constants.push_back(make_constant("colorTint", 3054254906u, 1.0f, 1.0f, 1.0f, 1.0f));
							constants.push_back(make_constant("bloomParams", 3733414975u, 1.0f, 0.0f, 0.0f, 0.0f));
							images.push_back(make_image("$identitynormalmap", 5, 1, 'n', 'p', HASH_NORMAL_MAP));
						}
						images.push_back(make_image(color, 2, 19, 'c', 'p', HASH_COLOR_MAP));
					}

					matdata["constantTable"] = constants;
					matdata["textureTable"] = images;

					const auto path = "materials\\"s + clean_name(name) + ".json"s;
					auto file = zonetool::filesystem::file(path);
					file.open("wb");
					file.write(matdata.dump(4, ' ', true, nlohmann::detail::error_handler_t::replace));
					file.close();
				}
			}

			void dump(Material* asset)
			{
				if (!asset || !asset->info.name)
				{
					return;
				}

				if (queued_set.insert(asset).second)
				{
					queued.push_back(asset);
				}
			}

			void note_model_materials(XModel* asset)
			{
				if (!asset || !asset->meshMaterials)
				{
					return;
				}

				for (auto i = 0; i < std::min<int>(asset->numLods, 8); i++)
				{
					const auto& mesh_material = asset->meshMaterials[i];
					for (auto j = 0; j < mesh_material.numMaterials; j++)
					{
						const auto* mat = mesh_material.materials[j];
						if (mat && mat->info.name)
						{
							auto mat_name = std::string(mat->info.name);
							if (!mat_name.empty() && mat_name[0] == ',')
							{
								mat_name.erase(0, 1);
							}
							model_materials.insert(mat_name);
						}
					}
				}
			}

			void flush()
			{
				for (auto* asset : queued)
				{
					try
					{
						write_json(asset, model_materials.contains(asset->info.name));
					}
					catch (const std::exception& e)
					{
						ZONETOOL_ERROR("Failed to convert material \"%s\": %s", asset->info.name, e.what());
					}
				}

				if (!queued.empty())
				{
					ZONETOOL_INFO("Converted %zu material(s) to H1 (%zu used by xmodels)", queued.size(), model_materials.size());
				}

				queued.clear();
				queued_set.clear();
				model_materials.clear();
			}
		}
	}
}
