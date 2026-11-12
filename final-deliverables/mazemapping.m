%% MAZE RECONSTRUCTION FROM ULTRASONIC SENSOR DATA
% CONSTANTS:
%   1. Sensor Mounting Offsets and Angles.
% INPUT:
%   1. Robot's X/Y position and yaw.
%   2. Front, left, right and rear ultrasonic sensor measurements.
% CALCULATION METHOD:
%   1. Locate, and read the sensor data.
%   2. Calculate each sensor position in world coordinates.
%   3. Project each measured distance along the sensor direction.
%   4. Plot the reconstructed wall points.

clear;
clc;
close all;

%% LOCATE THE DATA FILE

scriptFolder = fileparts(mfilename('fullpath'));
dataFile = fullfile(scriptFolder, 'sensordata.txt');

if ~isfile(dataFile)
    error('sensordata.txt was not found beside mazemapping.m');
end

%% READ

data = readtable(dataFile, 'FileType', 'text', 'Delimiter', '\t', 'VariableNamingRule', 'preserve');

robotX = data.x_m;
robotY = data.y_m;
robotYaw = data.yaw_rad;

fprintf('Loaded samples: %d\n', height(data));
fprintf('Final phase: %s\n', string(data.phase(end)));

%% SENSOR GEOMETRY
% Fixed sensor positions relative to the robot'S centre.

sensorNames = {'FRONT','LEFT','RIGHT','REAR'};

sensorOffsets = [ 0.243868103, -0.031798752;
    -0.132159041,  0.165551833;
    -0.132163624, -0.165500693;
    -0.247924932,  0.031713906];

% Front, left, right and rear sensor directions.

sensorAngles = [0;pi/2;-pi/2;pi];

distanceVars = {'front_m','left_m','right_m','rear_m'};

%% WORLD COORDINATES

wallPointsX = [];
wallPointsY = [];

for sensorIdx = 1:4

    sensorDistance = data.(distanceVars{sensorIdx});

    validReadings = isfinite(sensorDistance) & (sensorDistance > 0);

    sampleRows = find(validReadings);

    sensorWallX = zeros(numel(sampleRows),1);
    sensorWallY = zeros(numel(sampleRows),1);

    for pointIdx = 1:numel(sampleRows)

        sampleIdx = sampleRows(pointIdx);

        cosYaw = cos(robotYaw(sampleIdx));
        sinYaw = sin(robotYaw(sampleIdx));

        offsetWorldX = cosYaw * sensorOffsets(sensorIdx,1) - sinYaw * sensorOffsets(sensorIdx,2);

        offsetWorldY = sinYaw * sensorOffsets(sensorIdx,1) + cosYaw * sensorOffsets(sensorIdx,2);

        sensorWorldX = robotX(sampleIdx) + offsetWorldX;
        sensorWorldY = robotY(sampleIdx) + offsetWorldY;

        beamAngle = robotYaw(sampleIdx) + sensorAngles(sensorIdx);

        sensorWallX(pointIdx) = sensorWorldX + sensorDistance(sampleIdx) * cos(beamAngle);

        sensorWallY(pointIdx) = sensorWorldY + sensorDistance(sampleIdx) * sin(beamAngle);
    end

    wallPointsX = [wallPointsX; sensorWallX];
    wallPointsY = [wallPointsY; sensorWallY];

    fprintf('%s sensor: %d valid wall measurements.\n', sensorNames{sensorIdx}, numel(sampleRows));
end

%% PLOT

figure('Name','Ultrasonic Maze Reconstruction','Color','w');

scatter(wallPointsX, wallPointsY, 12, 'filled');
hold on;

plot(robotX, robotY, 'LineWidth', 1.5);

plot(robotX(1), robotY(1), 'o', 'MarkerSize', 8, 'LineWidth', 1.5);

plot(robotX(end), robotY(end), 's', 'MarkerSize', 8, 'LineWidth', 1.5);

axis equal;
grid on;

xlabel('World X (m)');
ylabel('World Y (m)');
title('Maze Reconstruction from Added Ultrasonic Sensors');

legend('Wall points','Robot path','Start position','End position','Location','best');