#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 13:19:26 2024

@author: johnnynienstedt
"""

import pybaseball
import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
from tqdm import tqdm
from itertools import combinations
from matplotlib.ticker import FuncFormatter



###########################################################################
######################## Get Pitch Data (~30 min) #########################
###########################################################################

print('Gathering Pitch Data for 2021')
pitch_data_2021 = pybaseball.statcast('2021-04-01', '2021-10-03')
print()
print('Gathering Pitch Data for 2022')
pitch_data_2022 = pybaseball.statcast('2022-04-07', '2022-10-05')
print()
print('Gathering Pitch Data for 2023')
pitch_data_2023 = pybaseball.statcast('2023-03-30', '2023-10-01')
print()
print('Gathering Pitch Data for 2024')
pitch_data_2024 = pybaseball.statcast('2024-03-28', '2024-9-27')

# remove deprecated/unnecessary columns
bad_cols = ['spin_rate_deprecated', 'break_angle_deprecated', 
            'break_length_deprecated', 'tfs_deprecated', 
            'tfs_zulu_deprecated', 'umpire', 'sv_id']
pitch_data_2021 = pitch_data_2021.drop(columns=bad_cols)
pitch_data_2022 = pitch_data_2022.drop(columns=bad_cols)
pitch_data_2023 = pitch_data_2023.drop(columns=bad_cols)
pitch_data_2024 = pitch_data_2024.drop(columns=bad_cols)

# reset indices
pitch_data_2021 = pitch_data_2021.reset_index()
pitch_data_2022 = pitch_data_2022.reset_index()
pitch_data_2023 = pitch_data_2023.reset_index()
pitch_data_2024 = pitch_data_2024.reset_index()
    
# combine all years
all_pitch_data = pd.concat([pitch_data_2021, pitch_data_2022, pitch_data_2023, pitch_data_2024])
all_pitch_data = all_pitch_data.reset_index()

# ensure values are present for necessary columns
necessary_cols = ['release_speed', 'zone', 'pfx_x', 'pfx_z', 'vx0', 'vy0', 'vz0', 'ax',
                  'ay', 'az', 'release_pos_x', 'release_pos_y', 'release_pos_z', 
                  'release_extension']
clean_pitch_data = all_pitch_data.copy().dropna(subset = necessary_cols)

# filter pitchers with at least 100 pitches thrown
pitcher_pitch_data = clean_pitch_data.groupby('pitcher').filter(lambda x: len(x) >= 100)

# flip axis for RHP so that +HB = arm side, -HB = glove side
mirror_cols = ['release_pos_x', 'plate_x', 'pfx_x', 'vx0', 'ax']
pitcher_pitch_data.loc[pitcher_pitch_data['p_throws'] == 'R', mirror_cols] = -pitcher_pitch_data.loc[pitcher_pitch_data['p_throws'] == 'R', mirror_cols]

# set break and release height in inches
clean_pitch_data['pfx_x'] = np.round(clean_pitch_data['pfx_x']*12)
clean_pitch_data['pfx_z'] = np.round(clean_pitch_data['pfx_z']*12)
pitcher_pitch_data['release_height'] = pitcher_pitch_data['release_pos_z']*12

# get primary pitch parameters (velo and acceleration in each dimension)
# this is measured roughly 50 feet from the plate (~5ft after release)
vx0 = pitcher_pitch_data['vx0']
vy0 = pitcher_pitch_data['vy0']
vz0 = pitcher_pitch_data['vz0']
ax = pitcher_pitch_data['ax']
ay = pitcher_pitch_data['ay']
az = pitcher_pitch_data['az']

# calculate vertical approach angle
y0 = 50
yf = 17/12
vyf = -np.sqrt(vy0**2- (2 * ay * (y0 - yf)))
t = (vyf - vy0)/ay
vzf = vz0 + (az*t)

theta_zf = -np.arctan(vzf/vyf)*180/np.pi
pitcher_pitch_data['VAA'] = round(theta_zf, 2)




###########################################################################
################################ Analysis #################################
###########################################################################




#
# Naive mound height estimate - mean RH at each park, visiting pitchers only
#




# mean ballpark release_height
ballpark_release_height = pitcher_pitch_data[pitcher_pitch_data.inning_topbot =='Bot'].groupby('home_team')['release_height'].mean()
sorted_release_height = ballpark_release_height.sort_values(ascending=False)

# for color purposes
norm = plt.Normalize(sorted_release_height.min(), sorted_release_height.max())

# make the plot
plt.figure(figsize=(12, 6))
bars = plt.bar(sorted_release_height.index, sorted_release_height, color=plt.cm.plasma(norm(sorted_release_height)))

# formatting
plt.title('Mean Release Height by Ballpark (2021-2024, visiting pitchers only)')
plt.ylim((66, 72))
plt.xlabel('Home Ballpark')
plt.ylabel('Mean Release Height (in)')
plt.text(22, 71, 'Data via Baseball Savant')
plt.xticks(rotation=45) # rotate x-axis labels for readability
plt.tight_layout()
plt.show()




#
# More rigorous mound height estimation - using pitcher unweighted average RH
#




# get data for fastballs only
pitcher_FF_data = pitcher_pitch_data[pitcher_pitch_data.pitch_type == 'FF']

# filter for pitchers who have thrown at least 100 FF at each park
filtered_FF_data = pitcher_FF_data.groupby(['player_name', 'home_team']).filter(lambda x: len(x) >= 100)

# aggregate by player and home_team
rh_pitcher_park = filtered_FF_data.groupby(['player_name', 'home_team'])['release_height'].mean().reset_index()

# unweighted average release height for each pitcher (one entry per park)
unweighted_avg_rh = rh_pitcher_park.groupby('player_name')['release_height'].mean().reset_index()
unweighted_avg_rh.rename(columns={'release_height': 'unweighted_avg_rh'}, inplace=True)
rh_pitcher_park = pd.merge(rh_pitcher_park, unweighted_avg_rh, on='player_name', how='left')

# add delta column
rh_pitcher_park['delta'] = rh_pitcher_park['release_height'] - rh_pitcher_park['unweighted_avg_rh']

# group by park and calculate the mean delta for each park
mean_delta_by_park = rh_pitcher_park.groupby('home_team')['delta'].mean()
sorted_delta_by_park = mean_delta_by_park.sort_values(ascending = False)

# get standard deviation
std_err_by_park = rh_pitcher_park.groupby('home_team')['delta'].std()
sorted_std_errors_by_park = std_err_by_park.loc[sorted_delta_by_park.index]

# plot
plt.figure(figsize=(9, 5))
norm = plt.Normalize(vmin=sorted_delta_by_park.min(), vmax=sorted_delta_by_park.max(), clip=True)

# scatterplot with error bars
plt.errorbar(
    sorted_delta_by_park.index,
    sorted_delta_by_park,
    yerr=sorted_std_errors_by_park,
    fmt='none',
    ecolor='grey',
    elinewidth=2,
    capsize=4,)

# color points based on height
points = plt.scatter(
    sorted_delta_by_park.index,
    sorted_delta_by_park,
    c=sorted_delta_by_park,
    cmap='coolwarm',
    norm=norm,
    s=100)

# formatting
plt.title("Estimated Relative Mound Height (Using pitchers' avg. release height at each ballpark)")
plt.xlabel('Ballpark')
plt.ylabel('Average Difference in Release Height (inches)')
plt.text(9.3, -2, 'Data via Baseball Savant, 2021-2024')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()




#
# Final estimate - using pairwise comparison
#




# generate all possible pairs of ballparks
ballparks = pitcher_FF_data['home_team'].unique()
ballpark_pairs = list(combinations(ballparks, 2))

# dictionary to store mean deltas and standard errors
mean_deltas = {}
std_errors = {}

# loop over all pairs
for park1, park2 in tqdm(ballpark_pairs):
    
    # filter to only include pitches thrown at the two parks
    filtered_df = pitcher_FF_data[pitcher_FF_data['home_team'].isin([park1, park2])]

    # group by pitcher and home_team, and count the number of pitches
    pitch_counts = filtered_df.groupby(['player_name', 'home_team']).size().unstack(fill_value=0)

    # filter pitchers who have thrown at least 100 pitches at both parks
    pitchers_with_enough_pitches = pitch_counts[(pitch_counts[park1] >= 80) & (pitch_counts[park2] >= 80)].index
    park_data = filtered_df[filtered_df['player_name'].isin(pitchers_with_enough_pitches)]

    # aggregate by player and home_team
    rh_pitcher_park = park_data.groupby(['player_name', 'home_team'])['release_height'].mean().reset_index()

    # unweighted average release height for each pitcher
    unweighted_avg_rh = rh_pitcher_park.groupby('player_name')['release_height'].mean().reset_index()
    unweighted_avg_rh.rename(columns={'release_height': 'unweighted_avg_rh'}, inplace=True)
    rh_pitcher_park = pd.merge(rh_pitcher_park, unweighted_avg_rh, on='player_name', how='left')

    # find difference between parks
    rh_pitcher_park['delta'] = rh_pitcher_park['release_height'] - rh_pitcher_park['unweighted_avg_rh']

    # calculate mean delta and standard error for each park
    mean_delta_by_park = rh_pitcher_park.groupby('home_team')['delta'].mean()
    std_err_by_park = rh_pitcher_park.groupby('home_team')['delta'].std()

    # store the results
    mean_deltas[(park1, park2)] = mean_delta_by_park
    std_errors[(park1, park2)] = std_err_by_park


# aggregate mean deltas and standard errors
final_mean_delta_by_park = pd.DataFrame(mean_deltas).mean(axis=1)
final_std_by_park = pd.DataFrame(std_errors).mean(axis=1)

# sort the results
final_mean_delta_by_park = final_mean_delta_by_park.sort_values(ascending=False)
final_std_by_park = final_std_by_park.loc[final_mean_delta_by_park.index]

# organize in dataframe
teams = pitcher_pitch_data['home_team'].unique()
team_deltas = pd.DataFrame(index=teams, columns=teams)
for team1 in teams:
    for team2 in teams:
        if team1 != team2:
            try:
                delta = mean_deltas[team1, team2] 
            except KeyError:
                delta = mean_deltas[team2, team1]
                
            team_deltas.at[team1, team2] = delta[team1]

# set diagonal values to 0 (self-comparison)
for team in teams:
    team_deltas.at[team, team] = 0

# set Oakland as universal reference point
for team in team_deltas.columns:
    team_deltas[team] = team_deltas[team] - team_deltas.loc['OAK', team]




#
# Plot all 30 distributions
#




# initialize figure
plt.figure(figsize=(12, 8))

# one scatterplot for each distribution
for team in final_mean_delta_by_park.index:

    values = team_deltas.loc[team]
    plt.scatter([team] * len(values), values, 
                label=team, 
                alpha=0.7,
                c = [final_mean_delta_by_park[team]*2]*len(values),
                cmap='coolwarm',
                norm=norm)

# formatting
plt.title('Release Height Differences Relative to Each Ballpark')
plt.xlabel('Home Team')
plt.ylabel('Difference in Release Height (inches)')
plt.xticks(rotation=30)
plt.tight_layout()
plt.show()




#
# Plot mean values with error bars instead
#




# aggregate all distributions
team_deltas['mean'] = team_deltas.mean(axis=1)
team_deltas['stdev'] = team_deltas.std(axis=1)
team_deltas = team_deltas.sort_values(by='mean', ascending=False)

# one scatterplot with error bars
plt.figure(figsize=(10,4))
plt.errorbar(team_deltas.index, team_deltas['mean'], 
             yerr=team_deltas['stdev'],
             fmt='none',
             ecolor='grey',
             elinewidth=2,
             capsize=4)

# color points based on the values
points = plt.scatter(
    team_deltas.index,
    team_deltas['mean'],
    c=team_deltas['mean']*2,
    cmap='coolwarm',
    norm=norm,
    s=100)

# formatting
plt.title('Estimated Relative Release Height by Ballpark - Pairwise Aggregation of Pitcher Avg. Release Heights')
plt.xlabel('Home Team')
plt.ylabel('Difference in Release Height (inches)')
plt.text(20, 0.7, 'Data via Baseball Savant, 2021-2024')
plt.text(8.5, -0.7, 'Error bars represent 1-$\\sigma$ confidence interval')
plt.text(10.2, -0.85, 'OAK set to zero for reference')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()




#
# Get data on high fastballs for analysis
#




# all high fastballs (between 3ft and 5ft off the ground)
high_FF_data = filtered_FF_data[(filtered_FF_data.plate_z > 3) &
                                (filtered_FF_data.plate_z < 5)].copy()

swstr_types = ['swinging_strike_blocked', 'swinging_strike', 'foul_tip']

# add whiff column
high_FF_data['whiff'] = high_FF_data['description'].isin(swstr_types).astype(int).copy()

# aggregate by ballpark
high_FF_by_park = high_FF_data.groupby('home_team').agg(
    whiff_rate=pd.NamedAgg(column='whiff', aggfunc='mean'),
    VAA=pd.NamedAgg(column='VAA', aggfunc='mean'),
).reset_index()

# add mound height column
high_FF_by_park['relative_mound_height'] = team_deltas['mean']

# change index to team names
high_FF_by_park.index = high_FF_by_park['home_team']
high_FF_by_park.drop(columns=['home_team'], inplace = True)  




#
# Mound height vs. high fastball VAA
#


               

# scatterplot
x = team_deltas['mean']
y = high_FF_by_park['VAA'].loc[x.index]
plt.scatter(x, y, s=10, alpha=0.7)

# label the parks with the highest and lowest release heights and VAAs
highest_x_idx = x.idxmax()
lowest_x_idx = x.idxmin()
highest_y_idx = y.idxmax()
lowest_y_idx = y.idxmin()
up_offset = 0.02
down_offset = -0.04

# highest mound
plt.text(x[highest_x_idx], y[highest_x_idx] + up_offset, highest_x_idx, 
          fontsize=12, ha='center', color='black', weight='bold')
# lowest mound
plt.text(x[lowest_x_idx], y[lowest_x_idx] + up_offset, lowest_x_idx,
          fontsize=12, ha='center', color='black', weight='bold')
# highest VAA
plt.text(x[highest_y_idx], y[highest_y_idx] + down_offset, highest_y_idx, 
          fontsize=12, ha='center', color='blue', weight='bold')
# lowest VAA
plt.text(x[lowest_y_idx], y[lowest_y_idx] + up_offset, lowest_y_idx, 
          fontsize=12, ha='center', color='red', weight='bold')

# linear regression for trendline
m, b, r, p, std_err = stats.linregress(x, y)
plt.plot([x.min(), x.max()],
         [x.min()*m + b, x.max()*m + b],
         '--', color = 'gray')

# formatting
plt.title('VAA on High FF vs. Est. Rel. Mound Height')
plt.xlabel('Estimated Relative Mound Height (inches)')
plt.ylabel('Vertical Approach Angle (FF, height 3ft - 5ft)')

height = y.max() - y.min()
width = x.max() - x.min()
top = height*0.9 + y.min()
bot = y.min()
left = x.min()
right = width*0.7 + x.min()

plt.text(-0.1, top, f'$R^2$ = {round(r**2, 2)}', fontsize = 12)
plt.text(right, bot, 'Data via Baseball Savant', fontsize = 8)
plt.show()




#
# Mound height vs. high fastball SwStr%
#




# scatterplot
x = team_deltas['mean']
y = high_FF_by_park['whiff_rate'].loc[x.index]
plt.scatter(x, y, s=10, alpha=0.7)

# label the parks with the highest and lowest release heights
highest_idx = x.idxmax()
lowest_idx = x.idxmin()
offset = -0.004

# highest mound
plt.text(x[highest_idx], y[highest_idx] + offset, highest_idx, 
          fontsize=10, ha='center', color='black', weight='bold')
# lowest mound
plt.text(x[lowest_idx], y[lowest_idx] + offset, lowest_idx,
          fontsize=10, ha='center', color='black', weight='bold')

# linear regression for trendline
m, b, r, p, std_err = stats.linregress(x, y)
plt.plot([x.min(), x.max()],
         [x.min()*m + b, x.max()*m + b],
         '--', color = 'gray')

# formatting
plt.title('SwStr% on High FF vs. Est. Rel. Mound Height')
plt.xlabel('Estimated Relative Mound Height (inches)')
plt.ylabel('SwStr% (FF, height 3ft - 5ft)')
plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{100*y:.0f}%'))

height = y.max() - y.min()
width = x.max() - x.min()
top = height*0.9 + y.min()
bot = y.min()
left = x.min()
right = width*0.7 + x.min()

plt.text(-0.55, 0.17, f'$R^2$ = {round(r**2, 2)}')
plt.text(right, bot, 'Data via Baseball Savant', fontsize = 8)
plt.show()
