#pragma once

// Bridge to atian-cod-tools (ACTS, https://github.com/ate47/atian-cod-tools).
//
// ACTS is vendored as a git submodule in deps/atian-cod-tools and built separately
// with CMake/vcpkg (see tools/build_acts.bat and docs/acts-integration.md). ZoneTool
// does not link ACTS: it runs the ACTS CLI (acts.exe) as a child process, so the two
// build systems (premake vs CMake + vcpkg) stay independent.
//
// This lets one zonetool.exe dump games that have no in-process ZoneTool module
// (BO4, Cold War, MW2019, Vanguard, MWII, MWIII, BO6, BO7) and gives access to the
// ACTS linkers, GSC tools and hash tools.

namespace acts
{
	struct game_info
	{
		const char* id;          // ZoneTool-side name (what the user types)
		const char* handler;     // ACTS fastfile handler (-r)
		const char* linker;      // ACTS fastfile linker (-l), nullptr if none
		const char* gsc_vm;      // ACTS gsc compiler game (-g), nullptr if unknown
		const char* description;
	};

	// all games ACTS can read fastfiles for
	const std::vector<game_info>& get_games();
	const game_info* find_game(const std::string& id);

	// path of acts.exe, empty if not found
	std::string find_executable();

	// run "acts.exe <args...>", returns the exit code (or -1 if acts.exe is missing)
	int run(const std::vector<std::string>& args);

	// Handles the command line before ZoneTool tries to find a game binary.
	// Returns an exit code when the command line was an ACTS command, std::nullopt otherwise.
	//
	//   zonetool -dumpzone <game> <zone|path.ff> [asset filter] [-- extra acts args]
	//   zonetool -linkzone <game> <input dir|file> [-- extra acts args]
	//   zonetool -gscdecompile <file|dir>... [-- extra acts args]
	//   zonetool -gsccompile <game vm> <file|dir>... [-- extra acts args]
	//   zonetool -hashlookup <hash|string>...
	//   zonetool -acts <raw acts arguments...>
	//
	// For -dumpzone, games that ZoneTool supports in-process (e.g. "t7"/"bo3" when the
	// BO3 server binary is present) are NOT intercepted unless -acts-force is passed.
	std::optional<int> handle_command_line();

	// in-process console helper ("acts <args>" command in game modules)
	void run_console_command(const std::vector<std::string>& args);
}
