// Taken from GoogleTest QuickStart:
// https://google.github.io/googletest/quickstart-cmake.html

#include <gtest/gtest.h>

TEST(HelloTest, BasicAssertions)
{
    EXPECT_STRNE("hello", "world");

    EXPECT_EQ(7 * 6, 42);
}

TEST(Test2, MoreBasicAssertions)
{
    EXPECT_FALSE(0);
    EXPECT_TRUE(1);
    EXPECT_TRUE(10);
    EXPECT_TRUE(true);
    EXPECT_EQ(3 + 1, 4);
}