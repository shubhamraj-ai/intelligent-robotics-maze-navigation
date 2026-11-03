-- Persistent Step-4 diagnostic: stable label read + camera read + image save.
-- Scene-owned script: no runtime creation/removal.
-- No logging calls, no dataset/session signals, no Python image transfer.

local LABEL_SIGNAL = 'step4_capture_label'
local MIN_STABLE_SECONDS = 0.75
local SAVE_INTERVAL_SECONDS = 2.00
local OUTPUT_DIR = 'C:/Users/user/Documents/IntelligentRobotics/intelligent-robotics-maze-navigation/dataset_simplified/_persistent_save_probe'

function sysCall_init()
    sim = require('sim')
    cameraHandle = sim.getObject('/PioneerP3DX/cam1')
    lastLabel = ''
    labelSince = sim.getSimulationTime()
    lastSave = {}
    counters = {
        forward = 0,
        left = 0,
        right = 0,
    }
end

local function validLabel(label)
    return label == 'forward'
        or label == 'left'
        or label == 'right'
end

function sysCall_sensing()
    local label = sim.getStringSignal(LABEL_SIGNAL)
    if label == nil or not validLabel(label) then
        label = ''
    end

    local now = sim.getSimulationTime()

    if label ~= lastLabel then
        lastLabel = label
        labelSince = now
        return
    end

    if label == '' then
        return
    end

    if now - labelSince < MIN_STABLE_SECONDS then
        return
    end

    local previous = lastSave[label]
    if previous ~= nil and now - previous < SAVE_INTERVAL_SECONDS then
        return
    end

    local image, resolution = sim.getVisionSensorImg(cameraHandle, 1)
    if image == nil or resolution == nil then
        return
    end

    counters[label] = counters[label] + 1
    local filename = string.format(
        '%s/%s_%06d.jpg',
        OUTPUT_DIR,
        label,
        counters[label]
    )

    sim.saveImage(image, resolution, 2, filename, -1)
    lastSave[label] = now
end
