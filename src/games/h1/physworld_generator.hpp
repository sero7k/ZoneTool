#pragma once
#include "h1.hpp"

namespace zonetool::h1::generator::physworld
{
	PhysWorld* generate(clipMap_t* asset, utils::memory::allocator& allocator);
}
