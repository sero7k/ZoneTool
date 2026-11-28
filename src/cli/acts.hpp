#pragma once

// Runs the atian-cod-tools CLI (acts.exe, https://github.com/ate47/atian-cod-tools) as a child process.
// ACTS builds with CMake and vcpkg, so it is not linked into zonetool.exe. Build it with tools\\build_acts.bat
// or put a release acts.exe in acts\\ next to zonetool.exe. See docs/ACTS.md.

namespace zonetool::cli::acts
{
	struct game_info
	{
		const char* id;
		const char* handler;
		const char* linker;
		const char* gsc_vm;
		const char* description;
	};

	const std::vector<game_info>& get_games();
	const game_info* find_game(const std::string& id);

	std::string find_executable();
	int run(const std::vector<std::string>& args);

	int run_command(std::vector<std::string> args);
}
