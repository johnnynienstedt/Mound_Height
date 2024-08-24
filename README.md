# Mound Height
This research aims to quantify (and to a limited extent, explain) the variance in release height data at MLB parks, and to explore the effects of this variance on pitcher performance.

# Background:
This project arose from an odd feature I found in release height data while working on park effects for my pitch shape model: ballparks seem to influence a pitcher's release height to a significant degree. This should not be the case, since all MLB mounds are required to be precisely 10 feet above home plate, with a slope of one inch per foot. Mound height is supposedly enforced to a tolerance of just 1/16 of an inch. However, that claim is contradicted by the release height data, which shows a range much greater than that. There are two explanations for this inconsistency:
a) MLB mound height and/or slope is not properly regulated, or
b) The Hawk-Eye tracking system employed by MLB at all 30 parks is not properly calibrated.

# Method:
It took me quite a while to figure out a method which removes all possible pitcher bias, but I believe I have done so. Before I explain it, I feel obligated to share some intermediate steps, so that you appreciate why I had to utilize such a complex method. If you're not interested in the whys and wherefores, feel free to skip ahead to the RESULTS section.

While working on park effects for Shape+, I aggregated the values of several metrics at each ballpark. I was intrigued by the differences in release height, but initially assumed that it was due to different pitchers pitching at different parks; if one team employs a squad of 6'6" pitchers, it follows that the average release height at their home park ought to be higher. 

My first attempt at combating this bias was to select only pitches thrown by visiting pitchers. I was very surprised to still observe a range of roughly 2.5 inches from the lowest release height (Petco Park) to the highest (Citizen's Bank Park). However, this method is still vulnerable to selection bias, since pitchers pitch more regularly against their divisional rivals compared to league and inter-league foes (especially before 2023).

It was clear to me then that I needed some way of quanitfying the change in individual pitchers' release heights from ballpark to ballpark. I also realized using a pitcher's total average release height as his baseline would be unwise, because that is weighted by the number of pitches he's thrown at each ballpark. So instead I found the average release height of each pitcher (fastballs only) at each ballpark, and then averaged those averages for an unweighted baseline. Then the pitcher's ballpark averages could be compared to his baseline, and all bias would be removed. Or so I thought.

This method was good, much better than the original, but it still had one fatal flaw: most pitchers haven't pitched at every ballpark. If a pitcher had only thrown at parks with a high mound, his baseline would be artificially high. My next thought was to limit my dataset to pitchers who had pitched at all 30 parks, but there were only a handful, and the resulting estimates were far too noisy.

I am rather proud of my eventual solution. Bear with me, because it's a bit of a doozy. For a moment, let's only consider pitchers who have thrown at least 80 pitches at both the Oakland Coliseum and at Angel Stadium in the last four years. That's a rather large set of pitchers, so by using their average release heights at each park, we can come up with a fairly confident estimate for the difference in 'mound height' (I'll put it in quotes since it's still up for debate) between these two parks. Then, let's repeat that process for Oakland and Seattle, Oakland and Houston, and so on for the rest of the ballparks. Then we could have a fairly good idea of each park's 'mound height' relative to Oakland's. 

To get a better estimate, we can repeat this process for the other 29 parks, totalling 435 ballpark pairs, to come up with 30 distributions of relative mound height. Each of those distributions have the host park at zero, and the other parks grouped around it. To aggregate these distributions, we must set some point of reference; I stuck with Oakland, since it seemed to be of middling height, and set it to zero for each distribution. Then all 30 distributions could be averaged directly, leaving me with (I hope) a truly bias-free measurement of relative release heights at each ballpark.

As expected, removing pitcher biases reduced the measured variablilty in release height, but did not eliminate it completely.

# Results:
My final estimate is that MLB mounds range in height by roughly 1.2 inches, with Petco Park on the short end and Minute Maid Park at the tall end. Each estimate is relative, and each comes with a one-sigma error of roughly +/- 0.24 inches. See release_height_by_park.png for full results.

# Conclusions:
My next goal was to determine whether this variance is truly due to the mounds themselves, or due to mis-calibrations of the Hawk-Eye system. One metric that should be highly dependent on mound height is vertical approach angle, or VAA. Some quick trigonometry tells us that a pitcher must throw a ball just over a tenth of a degree more steeply downward to reach the plat from a mound 1 inch taller than usual. That's quite a small difference, but over a set of thousands of pitches, it is detectable.

And in fact we do observe a correlation –- weak but significant, with an R-squared value of 0.12 -- between estimated mound height and VAA. Now, you might be thinking that this doesn't prove anything, since if Hawk-Eye was mis-calibrated for mound height it would surely be similarly off for VAA. However, VAA is not actually measured directly by Hawk-Eye; it is calculated using the velocity and acceleration of the pitch, which should be much less liable to mis-calibration. So, score one for the real mound effects.

But not so fast. Since VAA changes between ballparks, it stands to reason that the quality of certain pitches also ought to be afftected. High riding fastballs are perhaps the single pitch most reliant on VAA, benefitting greatly from flatter approach angles. It stands to reason, then, that high fastballs thrown off tall mounds might not be as effective as those thrown off low mounds. However, this does not seem to be the case. My estimated mound height exhibits no correlation to high fastball SwStr%, whether in its raw form or normalized to the quality of the pitches. By my count, that evens the score at one apiece.

More research is necessary to determine the true cause of these fluctuations, and to determine their effects on pitcher performance. I will update this repository when I make progress in either regard.
