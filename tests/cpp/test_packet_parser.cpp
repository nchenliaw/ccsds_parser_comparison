#include <gtest/gtest.h>

TEST(BasicTest, Trivial)
{
    EXPECT_STRNE("hello", "world");

    EXPECT_EQ(7 * 6, 42);
}
