#include <std_include.hpp>
#include "converter.hpp"

#include <game.hpp>
#include <iw7/zone/loader.hpp>

namespace zonetool::convert::iw7_h1
{
	namespace
	{
		template <typename S>
		S* header_as(void* header)
		{
			return static_cast<S*>(header);
		}

		void dump_asset(const std::int32_t type, void* header)
		{
			namespace source = zonetool::iw7;
			namespace target = zonetool::iw7::converter::h1;

			const auto asset_type = static_cast<source::XAssetType>(type);
			target::fxeffectdef::note_dumped(asset_type, source::get_asset_name(asset_type, header));

			switch (type)
			{
			case source::ASSET_TYPE_COMWORLD:
				target::comworld::dump(header_as<source::ComWorld>(header));
				break;
			case source::ASSET_TYPE_FX:
				target::fxeffectdef::dump(header_as<source::FxEffectDef>(header));
				break;
			case source::ASSET_TYPE_VFX:
				target::createfx::note_vfx(source::get_asset_name(asset_type, header));
				target::particlesystem::dump(header_as<source::ParticleSystemDef>(header));
				break;
			case source::ASSET_TYPE_SCRIPTFILE:
				target::createfx::dump(header_as<source::ScriptFile>(header));
				break;
			case source::ASSET_TYPE_GFXWORLD:
				target::gfxworld::dump(header_as<source::GfxWorld>(header));
				break;
			case source::ASSET_TYPE_MAP_ENTS:
				target::mapents::dump(header_as<source::MapEnts>(header));
				break;
			case source::ASSET_TYPE_IMAGE:
				target::gfximage::dump(header_as<source::GfxImage>(header));
				break;
			case source::ASSET_TYPE_MATERIAL:
				target::material::dump(header_as<source::Material>(header));
				break;
			case source::ASSET_TYPE_XMODEL:
				target::xmodel::dump(header_as<source::XModel>(header));
				break;
			case source::ASSET_TYPE_XMODEL_SURFS:
				target::xsurface::dump(header_as<source::XModelSurfs>(header));
				break;
			default:
				break;
			}
		}

		void finish(const std::string& zone_name)
		{
			namespace target = zonetool::iw7::converter::h1;

			target::fxeffectdef::flush();
			target::createfx::finalize(zone_name);
		}
	}

	const converter& definition()
	{
		static const converter iw7_h1
		{
			.source = "iw7",
			.target = "h1",
			.dump_asset = dump_asset,
			.finish = finish,
		};

		return iw7_h1;
	}
}
