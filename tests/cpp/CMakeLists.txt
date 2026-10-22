add_executable(packet_parser_tests 
    test_cases_hello_world.cpp
    test_packet_parser.cpp
)
target_link_libraries(packet_parser_tests PRIVATE packet_parser GTest::gtest_main)

include(GoogleTest)
gtest_discover_tests(packet_parser_tests)
