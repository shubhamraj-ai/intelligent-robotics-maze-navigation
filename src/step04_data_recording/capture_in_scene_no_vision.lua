-- Step 4 diagnostic: retain the Lua sensing-script lifecycle but disable vision.
-- This file intentionally performs NO camera resolution, NO vision-sensor read,
-- and NO image/JPEG save. Python still sends the same tiny W/A/D label signal.

local LABEL_SIGNAL = 'step4_capture_label'
local MIN_STABLE_SECONDS = 0.75

function sysCall_init()
    sim = require('sim')
    lastLabel = ''
    labelSince = sim.getSimulationTime()
end

local function validLabel(label)
    return label == 'forward'
        or label == 'left'
        or label == 'right'
        or label == 'probe'
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
        sim.addLog(
            sim.verbosity_scriptinfos,
            'STEP4_NO_VISION_LABEL -> ' .. label
        )
        return
    end

    if label == '' then
        return
    end

    if now - labelSince < MIN_STABLE_SECONDS then
        return
    end

    -- Deliberately empty diagnostic boundary:
    -- no sim.getObject('/PioneerP3DX/cam1')
    -- no sim.getVisionSensorImg(...)
    -- no sim.saveImage(...)
end
