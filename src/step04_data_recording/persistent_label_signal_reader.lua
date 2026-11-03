-- Persistent Step-4 diagnostic: read one dynamic W/A/D label signal only.
-- Scene-owned script: no runtime creation/removal.
-- No camera lookup, no vision reads, no image saves, no dataset/session signals.

local LABEL_SIGNAL = 'step4_capture_label'

function sysCall_init()
    sim = require('sim')
    lastLabel = ''
    sim.addLog(sim.verbosity_scriptinfos, 'STEP4_PERSISTENT_SIGNAL_READ_INIT')
end

function sysCall_sensing()
    local label = sim.getStringSignal(LABEL_SIGNAL)
    if label == nil then
        label = ''
    end

    if label ~= lastLabel then
        lastLabel = label
        sim.addLog(
            sim.verbosity_scriptinfos,
            'STEP4_PERSISTENT_SIGNAL_READ -> ' .. label
        )
    end
end
