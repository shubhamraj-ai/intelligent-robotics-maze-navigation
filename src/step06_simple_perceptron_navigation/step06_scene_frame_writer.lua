-- Step 6 simple-perceptron frame handoff.
--
-- This deliberately preserves the stable Step-4 camera isolation boundary:
-- camera acquisition and JPEG writing stay inside a persistent scene-owned
-- Lua simulation script. Python never receives vision-sensor image buffers.
--
-- The first live qualification must use this conservative 2.00 s save cadence.
-- Do not reduce it in the same experiment that introduces autonomous actuation.

local STARTUP_STABLE_SECONDS = 0.75
local SAVE_INTERVAL_SECONDS = 2.00
local OUTPUT_DIR = 'C:/Users/user/Documents/IntelligentRobotics/intelligent-robotics-maze-navigation/step06_frames'

function sysCall_init()
    sim = require('sim')
    cameraHandle = sim.getObject('/PioneerP3DX/cam1')
    startedAt = sim.getSimulationTime()
    lastSave = nil
    counter = 0
end

function sysCall_sensing()
    local now = sim.getSimulationTime()

    if now - startedAt < STARTUP_STABLE_SECONDS then
        return
    end

    if lastSave ~= nil and now - lastSave < SAVE_INTERVAL_SECONDS then
        return
    end

    local image, resolution = sim.getVisionSensorImg(cameraHandle, 1)
    if image == nil or resolution == nil then
        return
    end

    counter = counter + 1
    local filename = string.format(
        '%s/step6_frame_%06d.jpg',
        OUTPUT_DIR,
        counter
    )

    sim.saveImage(image, resolution, 2, filename, -1)
    lastSave = now
end
