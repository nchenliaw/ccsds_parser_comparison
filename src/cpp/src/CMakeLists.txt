add_library(packet_parser)

target_sources(
    packet_parser
    PRIVATE 
    packet_parser.cpp
)
target_include_directories(packet_parser PUBLIC ${PROJECT_SOURCE_DIR}/include)

add_executable(run_packet_parser run_packet_parser.cpp)
target_link_libraries(run_packet_parser PRIVATE packet_parser)