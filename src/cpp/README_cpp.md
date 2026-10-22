# C++ Readme

- Note the high-level CMakeLists.txt in src/cpp/CMakeLists.txt

Build/Run:

```bash
cd src/cpp
cmake -B build
cmake --build build
ctest --test-dir build/cpp
```

Run tests:

```bash
# 1: Follow build instructions above
cd build
ctest
```
