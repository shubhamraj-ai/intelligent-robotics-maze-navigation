-- Step 4 internal vision capture.
-- Camera acquisition and JPEG writing occur entirely inside CoppeliaSim.
-- Python communicates only a tiny class-label string signal.

local LABEL_SIGNAL = 'step4_capture_label'
local DATASET_ROOT_SIGNAL = 'step4_dataset_root'
local SESSION_ID_SIGNAL = 'step4_session_id'

local MIN_STABLE_SECONDS = 0.75
local SAVE_INTERVAL_SECONDS = 2.00

function sysCall_init()
    sim = require('sim')
    cameraHandle = sim.getObject('/PioneerP3DX/cam1')
    lastLabel = ''
    labelSince = sim.getSimulationTime()
    lastCapture = {}
    counters = {
        forward = 0,
        left = 0,
        right = 0,
        probe = 0,
    }
end

local function validLabel(label)
    return label == 'forward'
        or label == 'left'
        or label == 'right'
        or label == 'probe'
end

local function captureFolder(label)
    if label == 'probe' then
        return '_probe'
    end
    return label
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

    local previous = lastCapture[label]
    if previous ~= nil and now - previous < SAVE_INTERVAL_SECONDS then
        return
    end

    local datasetRoot = sim.getStringSignal(DATASET_ROOT_SIGNAL)
    local sessionId = sim.getStringSignal(SESSION_ID_SIGNAL)
    if datasetRoot == nil or datasetRoot == '' or sessionId == nil or sessionId == '' then
        return
    end

    counters[label] = counters[label] + 1
    local folder = captureFolder(label)
    local filename = string.format(
        '%s/%s/%s_%s_%06d.jpg',
        datasetRoot,
        folder,
        sessionId,
        label,
        counters[label]
    )

    -- Important isolation boundary:
    -- these image APIs execute inside the simulation script, never in Python.
    local image, resolution = sim.getVisionSensorImg(cameraHandle, 1)
    sim.saveImage(image, resolution, 2, filename, -1)
    lastCapture[label] = now

    sim.addLog(
        sim.verbosity_scriptinfos,
        'STEP4_INTERNAL_CAPTURE ' .. label .. ' -> ' .. filename
    )
end
