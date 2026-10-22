# C++23 feature support: GCC, Clang, MSVC

Question (issue #57): which C++23 features are available in current GCC, Clang, and MSVC, so skills know which features they can safely recommend?

Retrieved: 2026-10-20.

## Primary source and caveats

- Primary table: cppreference, "Compiler support for C++23", https://en.cppreference.com/w/cpp/compiler_support/23 (revision oldid=169957). Cppreference's tables are compiled from the compilers' own status pages and release notes; they are the most complete single view of C++23 status, but they are an aggregator, not the compilers themselves.
- Per-compiler cross-checks to do before shipping a skill that depends on a feature:
  - GCC: C++ status page, https://gcc.gnu.org/projects/cxx-status.html (language), and libstdc++ status, https://gcc.gnu.org/onlinedocs/libstdc++/manual/status.html#status.iso.2023
  - Clang: C++ status page, https://clang.llvm.org/cxx_status.html, and libc++ status, https://libcxx.llvm.org/Status/Cxx23.html
  - MSVC: Microsoft STL C++23 status, https://github.com/microsoft/STL/wiki/Implementation-Status (and MSVC conformance notes, https://learn.microsoft.com/cpp/overview/visual-cpp-language-conformance)
- Versions below are as shown by cppreference on the date above. **MSVC versions are the `_MSC_VER`-style `19.xx` value** (the STL/compiler version); the Visual Studio release mapping was not re-verified against Microsoft's docs, so treat the VS label as unverified.
- "Clang" for library features means **libc++**, and "GCC" means **libstdc++**, since that is what cppreference reports. A feature can be present in libstdc++ and absent in libc++ (or vice versa) and still compile under that compiler's default library.
- Cppreference marks partial support with "(partial)"; a feature shown with only a version number is treated as complete.

## Language features

| Feature | Paper | GCC | Clang | MSVC | Notes |
| - | - | - | - | - | - |
| Explicit object member functions (deducing `this`) | P0847R7 | 14 | 18 (19 full) | 19.32 partial; 19.43 full | **Caution:** older MSVC only partial. Clang 18 is the first release with it, but cppreference lists 19 as the full version. |
| `if consteval` | P1938R3 | 12 | 14 | 19.44 | |
| `auto(x)` / `auto{x}` decay-copy | P0849R8 | 12 | 15 | 19.50 | |
| `#elifdef` / `#elifndef` | P2334R1 | 12 | 13 | 19.40 | |
| Multidimensional `operator[]` | P2128R6 | 12 | 15 | 19.42 | |
| `static operator()` | P1169R4 | 13 | 16 | 19.44 | |
| `static operator[]` | P2589R1 | 13 | 16 | 19.44 | |
| Literal suffix for `size_t` (`uz`/`z`) | P0330R8 | 11 | 13 | 19.43 | |
| Relaxing `constexpr` restrictions | P2448R2 | 13 | 17 (partial); 19 | 19.51 | |
| Non-literal variables in `constexpr` functions | P2242R3 | 12 | 15 | 19.43 | |
| `static constexpr` variables in `constexpr` functions | P2647R1 | 13 | 16 | 19.51 | |
| `[[assume]]` attribute | P1774R8 | 13 | 19 | 19.51 | **Caution:** Clang only from 19. |
| Extend init-statement of range-based `for` with alias-declaration | P2360R0 | 12 | 14 | 19.50 | |
| Labels at end of compound statements | P2324R2 | 13 | 16 | 19.51 | |
| Named universal character escapes `\N{...}` | P2071R2 | 13 | 15 | 19.51 | |
| Delimited escape sequences `\x{...}` | P2290R3 | 13 | 15 | 19.50 | |
| `#warning` | P2437R1 | 13 | 15 | 19.50 | |
| UTF-8 as portable source encoding | P2295R6 | 13 (with caveats) | 15 | 19.0 (Update 2) | |
| Requirements for extended floating-point types | P1467R9 | 13 | not listed | N/A | **Caution:** no Clang; MSVC lists N/A. Do not recommend `std::float32_t` etc. portably. |
| Class template argument deduction from inherited constructors | P2582R1 | 14 | not listed | 19.51 | **Caution:** not on Clang per cppreference. |
| Extending lifetime of temporaries in range-for initializer | P2644R1 / P2718R0 / CWG2659 | 15 | 19 | 19.51 | |
| `consteval` propagates up (DR20) | P2564R3 | 14 | 17 | 19.52 | |

Full cppreference table covers many more (DR items, encoding changes, `char8_t` fixes); the rows above are the ones a skill is most likely to mention.

## Library features

| Feature | Paper | GCC (libstdc++) | Clang (libc++) | MSVC STL | Notes |
| - | - | - | - | - | - |
| `std::expected` (`<expected>`) | P0323R12, P2549R1 | 12 | 16 | 19.33 | Safe on all three at current versions. |
| `std::expected` monadic operations | P2505R5 | 13 | 17 | 19.36 | |
| `std::print` / `<print>` | P2093R14, P2539R4 | 14 | 17 (partial); 18 | 19.37 | **Caution:** Clang partial before 18. Also check `<print>` availability in your target toolchain's libc++. |
| `std::format` ranges / formatting of ranges | P2286R8 | 15 | 16 | 19.37 (partial); 19.42 | |
| `std::mdspan` (`<mdspan>`) | P0009R18 and related | 16 | 17 (partial); 18 | 19.39 | **Caution:** libstdc++ only from GCC 16 per cppreference; GCC 16 is needed. |
| `std::flat_map` | P0429R9 | 15 | 20 | 19.51 | **Caution:** Clang needs libc++ 20+. |
| `std::flat_set` | P1222R4 | 15 | 21 | 19.51 | **Caution:** Clang needs libc++ 21+. |
| `std::move_only_function` | P0288R9 | 12 | not listed | 19.32 | **Caution:** not on libc++ per cppreference. |
| `std::generator` | P2502R2, P2787R0 | 14 | not listed | 19.43 | **Caution:** not on libc++ per cppreference. |
| `std::stacktrace` | P0881R7, P2301R1 | 12 (partial); 14 | not listed | 19.34 | **Caution:** not on libc++ per cppreference. |
| `std::unreachable` | P0627R6 | 12 | 15 | 19.32 | |
| `std::to_underlying` | P1682R3 | 11 | 13 | 19.30 | |
| `std::byteswap` | P1272R4 | 12 | 14 | 19.31 | |
| `std::string::contains` / `string_view::contains` | P1679R3 | 11 | 12 | 19.30 | |
| `std::invoke_r` | P2136R3 | 12 | 17 | 19.31 | |
| `std::forward_like` | P2445R1 | 14 | 16 | 19.34 | |
| `std::start_lifetime_as` | P2590R2, P2679R2 | 16 | not listed | 19.51 | **Caution:** GCC 16 only; not on libc++. |
| `std::is_implicit_lifetime` | P2674R1 | 16 | 20 | 19.51 | |
| `std::stdfloat` (`<stdfloat>`) | P1467R9 | 13 | not listed | 19.37 | **Caution:** no libc++ support listed. |
| `<stdatomic.h>` | P0943R6 | 12 | 15 | 19.31 | |
| Standard library modules (`import std;`) | P2465R3 | 15 (`*`) | 17 (partial) | 19.35 (partial); 19.36 | **Caution:** do not recommend `import std;` without a target-specific build setup. |

### Ranges additions

| Feature | Paper | GCC | Clang | MSVC | Notes |
| - | - | - | - | - | - |
| `views::zip`, `zip_transform`, `adjacent`, `adjacent_transform` | P2321R2 | 13 | 15 (partial); 22 | 19.33 (partial); 19.37 | **Caution:** Clang full only from libc++ 22. |
| `views::join_with` | P2441R2 | 13 | 21 | 19.34 | **Caution:** Clang 21+. |
| `views::chunk` / `views::slide` | P2442R1 | 13 | not listed | 19.33 | **Caution:** no libc++ listed. |
| `views::chunk_by` | P2443R1 | 13 | 18 | 19.33 | |
| `views::stride` | P1899R3 | 13 | 23 | 19.34 | **Caution:** Clang 23 only. |
| `views::repeat` | P2474R2 | 13 | 17 | 19.36 | |
| `views::as_rvalue` | P2446R2 | 13 | 16 | 19.34 | |
| `views::enumerate` | P2164R9 | 13 | 23 | 19.37 | **Caution:** Clang 23 only. |
| `views::as_const` | P2278R4 | 13 | not listed | 19.35 (partial); 19.36 | **Caution:** no libc++ listed. |
| `ranges::iota`, `ranges::shift_left`, `ranges::shift_right` | P2440R1 | 13 (partial); 16 | 23 | 19.34 | **Caution:** Clang 23 only. |
| `ranges::contains`, `ranges::contains_subrange` | P2302R4 | 13 | 19 | 19.34 | |
| `ranges::find_last*` | P1223R5 | 13 | 19 | 19.36 | |
| Ranges fold algorithms (`ranges::fold_left`, ...) | P2322R6 | 13 | 23 (libc++ 18 partial) | 19.35 | **Caution:** Clang 23 for full support. |
| `ranges::to` and container range constructors | P1206R7 | 14 (partial); 15 | 17 | 19.34 | |
| Pipe support for range adaptor closures | P2387R3 | 13 (partial); 14 | 19 | 19.34 | |
| `views::cartesian_product` | P2374R4, P2540R1 | 13 | not listed | 19.37 | **Caution:** no libc++ listed. |
| Ranges fixes (DR20) | various | 11–16 depending on item | 14–22 | 19.30–19.37 | Items vary; check per item before recommending. |

## Summary for skill authors

Safe to recommend across all three compilers at current versions (GCC ≥ 14, libc++ ≥ 17, MSVC ≥ 19.37 unless noted):

- `std::expected` and its monadic operations
- `std::unreachable`, `std::to_underlying`, `std::byteswap`, `std::string::contains`
- deducing `this` (with MSVC caveat: partial before 19.43)
- `std::print` (Clang 18+ for full support)
- `views::chunk_by`, `views::repeat`, `views::as_rvalue`, `ranges::to`, `ranges::contains`
- `if consteval`, `static operator()`, multidimensional `operator[]`, `#elifdef`

Use with a compiler gate or a version check:

- `std::flat_map` / `std::flat_set`: GCC 15+, libc++ 20+ / 21+, MSVC 19.51+.
- `std::mdspan`: GCC 16+ and libc++ 18+ (partial before).
- `std::generator`, `std::move_only_function`, `std::stacktrace`, `std::stdfloat`, `views::cartesian_product`: not confirmed on libc++.
- `std::start_lifetime_as`: GCC 16 only, not on libc++.
- `views::stride`, `views::enumerate`, `views::fold*`, `ranges::iota`, `ranges::shift_*`: Clang 23 only.
- `[[assume]]`: Clang 19+.
- `import std;` and standard library modules: not recommended without build-system setup.

## Open items

- Verify MSVC version-to-Visual-Studio mapping and the exact MSVC rows against Microsoft's conformance page; this report uses cppreference's `19.xx` values.
- Confirm the Clang 23 and libc++ 22/23 entries against the libc++ status page, since they depend on a release that may not be in every toolchain yet.
- Cppreference rows for `ranges::starts_with`-style items and some DR rows were not cleanly parsed in the retrieved copy; they are excluded above rather than guessed.
