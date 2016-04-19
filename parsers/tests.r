setwd("~//Documents/School/Stanford/Journalism/Thesis/agenda-parser")

test <- read.csv("docs/east_side_uhsd/classed_lines/east_side_uhsd_1-21-16_classed_lines.csv")

colnames(test)

check_success <- subset(test, select=c(line_class, text))

head(check_success)

check_success

write.csv(check_success, file = "test_output.csv")
