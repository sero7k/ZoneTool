#include <std_include.hpp>
#include "acts_bridge.hpp"

#include <utils/io.hpp>
#include <utils/string.hpp>

namespace acts
{
	namespace
	{
		std::vector<std::string> get_args()
		{
			int argc = 0;
			LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);

			std::vector<std::string> args;
			if (!argv)
			{
				return args;
			}

			for (int i = 0; i < argc; i++)
			{
				const std::wstring warg = argv[i];
				const auto len = WideCharToMultiByte(CP_UTF8, 0, warg.data(), static_cast<int>(warg.size()), nullptr, 0, nullptr, nullptr);
				std::string arg(static_cast<size_t>(len), '\0');
				WideCharToMultiByte(CP_UTF8, 0, warg.data(), static_cast<int>(warg.size()), arg.data(), len, nullptr, nullptr);
				args.emplace_back(std::move(arg));
			}

			LocalFree(argv);
			return args;
		}

		std::string lower(std::string str)
		{
			std::transform(str.begin(), str.end(), str.begin(), [](const unsigned char c)
			{
				return static_cast<char>(std::tolower(c));
			});
			return str;
		}

		// quote one argument following the CommandLineToArgvW rules
		std::wstring quote_arg(const std::string& arg)
		{
			std::wstring warg;
			{
				const auto len = MultiByteToWideChar(CP_UTF8, 0, arg.data(), static_cast<int>(arg.size()), nullptr, 0);
				warg.resize(static_cast<size_t>(len));
				MultiByteToWideChar(CP_UTF8, 0, arg.data(), static_cast<int>(arg.size()), warg.data(), len);
			}

			if (!warg.empty() && warg.find_first_of(L" \t\n\v\"") == std::wstring::npos)
			{
				return warg;
			}

			std::wstring out = L"\"";
			for (auto it = warg.begin(); ; ++it)
			{
				size_t backslashes = 0;
				while (it != warg.end() && *it == L'\\')
				{
					++it;
					++backslashes;
				}

				if (it == warg.end())
				{
					out.append(backslashes * 2, L'\\');
					break;
				}

				if (*it == L'"')
				{
					out.append(backslashes * 2 + 1, L'\\');
					out.push_back(*it);
				}
				else
				{
					out.append(backslashes, L'\\');
					out.push_back(*it);
				}
			}
			out.push_back(L'"');
			return out;
		}

		std::optional<std::string> take_option(std::vector<std::string>& args, const std::string& name)
		{
			for (size_t i = 0; i + 1 < args.size(); i++)
			{
				if (args[i] == name)
				{
					auto value = args[i + 1];
					args.erase(args.begin() + i, args.begin() + i + 2);
					return value;
				}
			}
			return {};
		}

		bool take_flag(std::vector<std::string>& args, const std::string& name)
		{
			const auto it = std::find(args.begin(), args.end(), name);
			if (it == args.end())
			{
				return false;
			}
			args.erase(it);
			return true;
		}

		// everything after "--" is forwarded to acts verbatim
		std::vector<std::string> split_passthrough(std::vector<std::string>& args)
		{
			const auto it = std::find(args.begin(), args.end(), "--");
			if (it == args.end())
			{
				return {};
			}

			std::vector<std::string> extra(it + 1, args.end());
			args.erase(it, args.end());
			return extra;
		}

		std::string resolve_fastfile(const std::string& zone, const std::optional<std::string>& game_path)
		{
			if (std::filesystem::exists(zone))
			{
				return zone;
			}

			std::vector<std::filesystem::path> candidates;
			const auto ff = zone.ends_with(".ff") ? zone : zone + ".ff";

			if (game_path.has_value())
			{
				candidates.emplace_back(std::filesystem::path(*game_path) / "zone" / ff);
				candidates.emplace_back(std::filesystem::path(*game_path) / ff);
			}

			candidates.emplace_back(std::filesystem::path("zone") / ff);
			candidates.emplace_back(ff);

			for (const auto& candidate : candidates)
			{
				if (std::filesystem::exists(candidate))
				{
					return candidate.string();
				}
			}

			// let acts report the error (or resolve it through casc with -C)
			return zone;
		}

		// games ZoneTool can dump in-process, these are never intercepted unless -acts-force is set
		bool has_inprocess_module(const std::string& game)
		{
			const auto g = lower(game);
			if (g == "t7" || g == "bo3")
			{
				return utils::io::file_exists("BlackOps3_UnrankedDedicatedServer.exe");
			}

			return false;
		}

		void print_usage()
		{
			printf("ZoneTool ACTS bridge commands:\n");
			printf("  -dumpzone <game> <zone|file.ff> [asset types] [-gamepath <dir>] [-o <dir>] [-- acts args]\n");
			printf("  -linkzone <game> <input> [-o <dir>] [-- acts args]\n");
			printf("  -gscdecompile <file|dir>... [-o <dir>] [-- acts args]\n");
			printf("  -gsccompile <game> <file|dir>... [-o <dir>] [-- acts args]\n");
			printf("  -hashlookup <hash|string>...\n");
			printf("  -acts <raw acts arguments>\n");
			printf("  -actspath <path to acts.exe>   (or env ZONETOOL_ACTS)\n");
			printf("games:\n");
			for (const auto& game : get_games())
			{
				printf("  %-8s %s%s\n", game.id, game.description, game.linker ? " [linker]" : "");
			}
		}

		std::optional<std::string> g_acts_path_override;
	}

	const std::vector<game_info>& get_games()
	{
		// handler ids from ACTS src/core/acts/tools/fastfile/handlers/handler_game_*.cpp
		// linker ids from ACTS src/core/acts/tools/fastfile/linkers/linker_*.cpp
		// gsc vm names from ACTS src/core/acts/tools/gsc/vm/*.cpp (RegisterVmName)
		static const std::vector<game_info> games =
		{
			{"bo3", "bo3", "Bo3", "t7", "Black Ops 3 (T7)"},
			{"t7", "bo3", "Bo3", "t7", "Black Ops 3 (T7)"},
			{"bo4", "bo4", "Bo4", "t8", "Black Ops 4 (T8)"},
			{"t8", "bo4", "Bo4", "t8", "Black Ops 4 (T8)"},
			{"cw", "cw", "CW", "t9", "Black Ops Cold War (T9)"},
			{"t9", "cw", "CW", "t9", "Black Ops Cold War (T9)"},
			{"mw19", "mw19", nullptr, "iw8", "Modern Warfare 2019 (IW8)"},
			{"iw8", "mw19", nullptr, "iw8", "Modern Warfare 2019 (IW8)"},
			{"vg", "vg", nullptr, nullptr, "Vanguard (S4)"},
			{"mwii", "mwii", nullptr, nullptr, "Modern Warfare II (IW9)"},
			{"mwiisp", "mwiisp", nullptr, nullptr, "Modern Warfare II Campaign"},
			{"mwiii", "mwiii", nullptr, "jup", "Modern Warfare III (JUP)"},
			{"mwiiisp", "mwiiisp", nullptr, "jup", "Modern Warfare III Campaign"},
			{"bo6", "bo6", nullptr, "t10", "Black Ops 6 (T10)"},
			{"bo6sp", "bo6sp", nullptr, "t10sp", "Black Ops 6 Campaign"},
			{"bo7", "bo7", nullptr, "sat", "Black Ops 7 (SAT)"},
		};

		return games;
	}

	const game_info* find_game(const std::string& id)
	{
		const auto lid = lower(id);
		for (const auto& game : get_games())
		{
			if (lid == game.id)
			{
				return &game;
			}
		}
		return nullptr;
	}

	std::string find_executable()
	{
		std::vector<std::filesystem::path> candidates;

		if (g_acts_path_override.has_value())
		{
			candidates.emplace_back(*g_acts_path_override);
		}

		char env[MAX_PATH]{};
		if (GetEnvironmentVariableA("ZONETOOL_ACTS", env, sizeof(env)) > 0)
		{
			candidates.emplace_back(env);
		}

		char self[MAX_PATH]{};
		GetModuleFileNameA(nullptr, self, sizeof(self));
		const auto self_dir = std::filesystem::path(self).parent_path();

		for (const auto& base : { self_dir, std::filesystem::current_path() })
		{
			candidates.emplace_back(base / "acts.exe");
			candidates.emplace_back(base / "acts" / "acts.exe");
			candidates.emplace_back(base / "acts" / "bin" / "acts.exe");
		}

		for (auto candidate : candidates)
		{
			if (std::filesystem::is_directory(candidate))
			{
				candidate /= "acts.exe";
			}

			if (std::filesystem::exists(candidate))
			{
				return candidate.string();
			}
		}

		return {};
	}

	int run(const std::vector<std::string>& args)
	{
		const auto exe = find_executable();
		if (exe.empty())
		{
			printf("[acts] acts.exe not found. Build it with tools\\build_acts.bat or download it from\n"
				"       https://github.com/ate47/atian-cod-tools/releases, then put it in \"acts\\\" next to\n"
				"       zonetool.exe, or pass -actspath <path> / set ZONETOOL_ACTS.\n");
			return -1;
		}

		std::wstring cmdline = quote_arg(exe);
		for (const auto& arg : args)
		{
			cmdline += L" ";
			cmdline += quote_arg(arg);
		}

		printf("[acts] %s", exe.data());
		for (const auto& arg : args)
		{
			printf(" %s", arg.data());
		}
		printf("\n");

		STARTUPINFOW si{};
		si.cb = sizeof(si);
		PROCESS_INFORMATION pi{};

		std::vector<wchar_t> buffer(cmdline.begin(), cmdline.end());
		buffer.push_back(L'\0');

		// keep ZoneTool's working directory so relative paths given by the user stay valid;
		// acts finds its own data (hash index, deps/) through its executable path
		if (!CreateProcessW(nullptr, buffer.data(), nullptr, nullptr, FALSE, 0, nullptr, nullptr, &si, &pi))
		{
			printf("[acts] failed to start acts (error %lu)\n", GetLastError());
			return -1;
		}

		WaitForSingleObject(pi.hProcess, INFINITE);

		DWORD code = 0;
		GetExitCodeProcess(pi.hProcess, &code);

		CloseHandle(pi.hThread);
		CloseHandle(pi.hProcess);

		return static_cast<int>(code);
	}

	namespace
	{
		int dump_zone(std::vector<std::string> args)
		{
			// args: <game> <zone> [asset types]
			auto extra = split_passthrough(args);
			const auto game_path = take_option(args, "-gamepath");
			const auto output = take_option(args, "-o");

			if (args.size() < 2)
			{
				print_usage();
				return 1;
			}

			const auto* game = find_game(args[0]);
			if (!game)
			{
				printf("[acts] unknown game \"%s\"\n", args[0].data());
				print_usage();
				return 1;
			}

			std::vector<std::string> acts_args =
			{
				"fastfile",
				resolve_fastfile(args[1], game_path),
				"-r", game->handler,
				"-o", output.value_or("dump/"s + game->handler),
			};

			if (args.size() >= 3 && args[2] != "_")
			{
				acts_args.emplace_back("-a");
				acts_args.emplace_back(args[2]);
			}

			if (game_path.has_value())
			{
				acts_args.emplace_back("-G");
				acts_args.emplace_back(*game_path);
			}

			acts_args.insert(acts_args.end(), extra.begin(), extra.end());
			return run(acts_args);
		}

		int link_zone(std::vector<std::string> args)
		{
			auto extra = split_passthrough(args);
			const auto output = take_option(args, "-o");

			if (args.size() < 2)
			{
				print_usage();
				return 1;
			}

			const auto* game = find_game(args[0]);
			if (!game || !game->linker)
			{
				printf("[acts] no ACTS linker for game \"%s\" (linkers exist for bo3, bo4 and cw)\n", args[0].data());
				return 1;
			}

			std::vector<std::string> acts_args = { "fastfilelinker", args[1], "-l", game->linker };
			if (output.has_value())
			{
				acts_args.emplace_back("-o");
				acts_args.emplace_back(*output);
			}

			acts_args.insert(acts_args.end(), extra.begin(), extra.end());
			return run(acts_args);
		}

		int gsc_decompile(std::vector<std::string> args)
		{
			auto extra = split_passthrough(args);
			const auto output = take_option(args, "-o");

			if (args.empty())
			{
				print_usage();
				return 1;
			}

			// "gscinfo -g" = produce gsc source
			std::vector<std::string> acts_args = { "gscinfo", "-g" };
			acts_args.insert(acts_args.end(), args.begin(), args.end());
			acts_args.emplace_back("-o");
			acts_args.emplace_back(output.value_or("dump/gsc"));
			acts_args.insert(acts_args.end(), extra.begin(), extra.end());
			return run(acts_args);
		}

		int gsc_compile(std::vector<std::string> args)
		{
			auto extra = split_passthrough(args);
			const auto output = take_option(args, "-o");

			if (args.size() < 2)
			{
				print_usage();
				return 1;
			}

			std::string vm = args[0];
			if (const auto* game = find_game(args[0]); game && game->gsc_vm)
			{
				vm = game->gsc_vm;
			}

			std::vector<std::string> acts_args = { "gscc", "-g", vm };
			acts_args.insert(acts_args.end(), args.begin() + 1, args.end());
			if (output.has_value())
			{
				acts_args.emplace_back("-o");
				acts_args.emplace_back(*output);
			}
			acts_args.insert(acts_args.end(), extra.begin(), extra.end());
			return run(acts_args);
		}

		int hash_lookup(const std::vector<std::string>& args)
		{
			std::vector<std::string> acts_args = { "lookup" };
			acts_args.insert(acts_args.end(), args.begin(), args.end());
			return run(acts_args);
		}
	}

	std::optional<int> handle_command_line()
	{
		auto args = get_args();
		if (args.size() < 2)
		{
			return {};
		}

		// drop argv[0]
		args.erase(args.begin());

		g_acts_path_override = take_option(args, "-actspath");
		const auto force = take_flag(args, "-acts-force");

		if (args.empty())
		{
			return {};
		}

		const auto command = args[0];
		std::vector<std::string> rest(args.begin() + 1, args.end());

		if (command == "-acts")
		{
			if (rest.empty())
			{
				print_usage();
				return 1;
			}
			return run(rest);
		}

		if (command == "-actshelp")
		{
			print_usage();
			return 0;
		}

		if (command == "-dumpzone")
		{
			// "-dumpzone <zone>" (no game) is the in-process ZoneTool command
			if (rest.size() < 2 || !find_game(rest[0]))
			{
				return {};
			}

			if (!force && has_inprocess_module(rest[0]))
			{
				return {};
			}

			return dump_zone(rest);
		}

		if (command == "-linkzone")
		{
			return link_zone(rest);
		}

		if (command == "-gscdecompile")
		{
			return gsc_decompile(rest);
		}

		if (command == "-gsccompile")
		{
			return gsc_compile(rest);
		}

		if (command == "-hashlookup")
		{
			return hash_lookup(rest);
		}

		return {};
	}

	void run_console_command(const std::vector<std::string>& args)
	{
		if (args.empty())
		{
			print_usage();
			return;
		}

		const auto code = run(args);
		printf("[acts] exited with code %d\n", code);
	}
}
