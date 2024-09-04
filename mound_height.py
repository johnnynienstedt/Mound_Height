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
pitch_data = clean_pitch_data.groupby('pitcher').filter(lambda x: len(x) >= 100)

# flip axis for RHP so that +HB = arm side, -HB = glove side
mirror_cols = ['release_pos_x', 'plate_x', 'pfx_x', 'vx0', 'ax']
pitch_data.loc[pitch_data['p_throws'] == 'R', mirror_cols] = -pitch_data.loc[pitch_data['p_throws'] == 'R', mirror_cols]

# set break and release height in inches
pitch_data['pfx_x'] = np.round(pitch_data['pfx_x']*12)
pitch_data['pfx_z'] = np.round(pitch_data['pfx_z']*12)
pitch_data['release_height'] = pitch_data['release_pos_z']*12

# get primary pitch parameters (velo and acceleration in each dimension)
# this is measured roughly 50 feet from the plate (~5ft after release)
vx0 = pitch_data['vx0']
vy0 = pitch_data['vy0']
vz0 = pitch_data['vz0']
ax = pitch_data['ax']
ay = pitch_data['ay']
az = pitch_data['az']

# calculate vertical approach angle
y0 = 50
yf = 17/12
vyf = -np.sqrt(vy0**2- (2 * ay * (y0 - yf)))
t = (vyf - vy0)/ay
vzf = vz0 + (az*t)

theta_zf = -np.arctan(vzf/vyf)*180/np.pi
pitch_data['VAA'] = round(theta_zf, 2)




###########################################################################
################################ Analysis #################################
###########################################################################




# generate all possible pairs of ballparks
ballparks = np.sort(pitch_data['home_team'].unique())
ballpark_pairs = list(combinations(ballparks, 2))

# dataframe to store park effects for this statistic
mean_deltas = pd.DataFrame(columns=list(ballparks), index=ballparks, dtype=float)
for park in ballparks:
    mean_deltas.loc[park, park] = 0

# loop over pairs
pitchers_used = []
rh_std = []
rh_mean = np.abs(pitch_data['release_height'].mean())
for park1, park2 in tqdm(ballpark_pairs):
    
    # filter to only include events at the two parks
    filtered_by_park = pitch_data[pitch_data['home_team'].isin([park1, park2])]
    
    # group by player and park and count the number of events
    pitch_counts = filtered_by_park.groupby(['pitcher', 'home_team']).size().unstack(fill_value=0)
   
    # filter players who have experienced enough events at both parks
    enough_pitches = pitch_counts[(pitch_counts[park1] >= 10) & (pitch_counts[park2] >= 10)].index
    pitcher_pitch_error = filtered_by_park[filtered_by_park['pitcher'].isin(enough_pitches)].copy().groupby('pitcher').sem(numeric_only=True)['release_height']
    
    # filter players with error less than 10%
    pitchers_with_low_error = pitcher_pitch_error[pitcher_pitch_error < 0.1*rh_mean]
        
    # get pitch_data for good players
    pitchers_used.append(len(pitchers_with_low_error))
    pitcher_data = filtered_by_park[filtered_by_park['pitcher'].isin(pitchers_with_low_error.index)].copy()
    rh_std.append(pitcher_data.groupby('pitcher')['release_height'].std().mean())

    # aggregate by player and park
    rh_pitcher_park = pitcher_data.groupby(['pitcher', 'home_team'])['release_height'].mean().reset_index()

    # unweighted average of statistic for each player
    unweighted_avg_rh = rh_pitcher_park.groupby('pitcher')['release_height'].mean().reset_index()
    unweighted_avg_rh.rename(columns={'release_height': 'unweighted_avg_rh'}, inplace=True)
    rh_pitcher_park = pd.merge(rh_pitcher_park, unweighted_avg_rh, on='pitcher', how='left')

    # find difference between parks
    rh_pitcher_park['delta'] = rh_pitcher_park['release_height'] - rh_pitcher_park['unweighted_avg_rh']

    # calculate mean delta and standard error for each park
    mean_delta_by_park = rh_pitcher_park.groupby('home_team')['delta'].mean()

    # store the results
    mean_deltas.loc[park1, park2] = mean_delta_by_park[0]
    mean_deltas.loc[park2, park1] = mean_delta_by_park[1]


# aggregate means and errors for each park
park_mean = mean_deltas.mean(axis=1)
park_stderr = mean_deltas.sem(axis=1)
mean_deltas['park_mean'] = park_mean
mean_deltas['park_stderr'] = park_stderr
mean_deltas.sort_values(by='park_mean', ascending=False, inplace=True)

# min and max diff
max_d = mean_deltas['park_mean'].max()
min_d = mean_deltas['park_mean'].min()

# min and max z-score
rh_std = np.mean(rh_std)
max_z = NormalDist(mu=0, sigma=rh_std).zscore(max_d)
min_z = NormalDist(mu=0, sigma=rh_std).zscore(min_d)
effect = round((max_z - min_z)/2, 2)

diff = round((max_d - min_d)/2, 2)

print()
print('Min. ', np.min(pitchers_used), 'pitchers used per park pair.')
print('Releease height varies by +/-' + str(diff) + ' inches (+/-' + str(effect) + ' standard deviations) due to park effects.')
print()    




#
# Plot park estimates with error bars
#




# one scatterplot with error bars
fig, ax = plt.subplots(figsize=(10,5))
x = mean_deltas.index
y = mean_deltas['park_mean']

plt.errorbar(x, y, 
             yerr=mean_deltas['park_stderr'],
             fmt='none',
             ecolor='grey',
             elinewidth=2,
             capsize=4)

# color points based on the values
plt.scatter(x, y,
            c=y,
            cmap='coolwarm',
            norm=plt.Normalize(y.min(), y.max()),
            s=100)

# formatting
ax.set_title('Estimated Relative Release Height by Ballpark - Pairwise Aggregation of Pitcher Avg. Release Heights')
ax.set_xlabel('Home Team')
ax.set_ylabel('Release Height Added (inches)')
ax.tick_params(axis='x', rotation=45)

# text
y_limits = ax.get_ylim()
bot = y_limits[0] + 0.1*(y_limits[1] - y_limits[0])
top = y_limits[1] - 0.1*(y_limits[1] - y_limits[0])
ax.text(25, top, 'Data via Baseball Savant, 2021-2024', ha='center', va='top')
ax.text(15, bot, 'Error bars represent standard error (N = 30)', ha='center', va='top')
plt.tight_layout()
plt.show()




#
# Get data on high fastballs for analysis
#




# all high fastballs (between 3ft and 5ft off the ground)
high_FF_data = pitch_data.query('pitch_type == "FF" and plate_z > 3 and plate_z < 5').copy()

# add whiff column
swstr_types = ['swinging_strike_blocked', 'swinging_strike', 'foul_tip']
high_FF_data['whiff'] = high_FF_data['description'].isin(swstr_types).astype(int).copy()

# aggregate by ballpark
high_FF_by_park = high_FF_data.groupby('home_team').agg(
    whiff_rate=pd.NamedAgg(column='whiff', aggfunc='mean'),
    VAA=pd.NamedAgg(column='VAA', aggfunc='mean'),
).reset_index()

# add mound height column
high_FF_by_park['relative_mound_height'] = mean_deltas['park_mean']

# change index to team names
high_FF_by_park.index = high_FF_by_park['home_team']
high_FF_by_park.drop(columns=['home_team'], inplace = True)  




#
# Mound height vs. high fastball VAA
#


               

# scatterplot
fig, ax = plt.subplots()
x = mean_deltas['park_mean']
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
ax.text(x[highest_x_idx], y[highest_x_idx] + up_offset, highest_x_idx, 
          fontsize=12, ha='center', color='black', weight='bold')
# lowest mound
ax.text(x[lowest_x_idx], y[lowest_x_idx] + up_offset, lowest_x_idx,
          fontsize=12, ha='center', color='black', weight='bold')
# highest VAA
ax.text(x[highest_y_idx], y[highest_y_idx] + down_offset, highest_y_idx, 
          fontsize=12, ha='center', color='blue', weight='bold')
# lowest VAA
ax.text(x[lowest_y_idx], y[lowest_y_idx] + up_offset, lowest_y_idx, 
          fontsize=12, ha='center', color='red', weight='bold')

# linear regression for trendline
m, b, r, p, std_err = stats.linregress(x, y)
plt.plot([x.min(), x.max()],
         [x.min()*m + b, x.max()*m + b],
         '--', color = 'gray')

# formatting
ax.set_title('VAA on High FF vs. Est. Rel. Mound Height')
ax.set_xlabel('Estimated Relative Mound Height (inches)')
ax.set_ylabel('Vertical Approach Angle (FF, height 3ft - 5ft)')

height = y.max() - y.min()
width = x.max() - x.min()
top = height*0.9 + y.min()
bot = y.min()
left = x.min()
right = width*0.7 + x.min()

# text
y_limits = ax.get_ylim()
bot = y_limits[0] + 0.1*(y_limits[1] - y_limits[0])
top = y_limits[1] - 0.1*(y_limits[1] - y_limits[0])
ax.text(left + width*(3/4), bot, 'Data via Baseball Savant, 2021-2024', ha='center', va='top')
ax.text(left + width*(7/8), top, f'$R^2$ = {round(r**2, 2)}', fontsize = 12, ha='center', va='top')
plt.tight_layout()
plt.show()
