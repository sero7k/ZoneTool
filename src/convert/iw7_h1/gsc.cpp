#include <std_include.hpp>
#include "gsc.hpp"

namespace zonetool::iw7::converter::h1
{
	xsk::gsc::iw7::context& gsc_context()
	{
		static xsk::gsc::iw7::context context{xsk::gsc::instance::server};
		return context;
	}
}
