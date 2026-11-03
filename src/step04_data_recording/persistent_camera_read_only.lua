-- Persistent Step-4 diagnostic: stable label read + camera read only.
-- Scene-owned script: no runtime creation/removal.
-- No image-file writing, no dataset/session signals, no logging calls.

local LABEL_SIGNAL = 'step4_capture_label'
local MIN_STABLE_SECONDS = 0.75
local READ_INTERVAL_SECONDS = 2.00

function sysCall_init()
    sim = require('sim')
    cameraHandle = sim.getObject('/PioneerP3DX/cam1')
    lastLabel = ''
    labelSince = sim.getSimulationTime()
    lastRead = {}
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

    local previous = lastRead[label]
    if previous ~= nil and now - previous < READ_INTERVAL_SECONDS then
        return
    end

    -- Deliberately read and discard the image.
    -- No image-file write and no image data is transferred to Python.
    local image, resolution = sim.getVisionSensorImg(cameraHandle, 1)
    if image ~= nil and resolution ~= nil then
        lastRead[label] = now
    end
end
