-- Step-4 diagnostic: temporary Lua lifecycle only.
-- No string signals, no camera lookup, no vision-sensor reads, no image saves.

function sysCall_init()
    sim = require('sim')
    sim.addLog(sim.verbosity_scriptinfos, 'STEP4_LUA_LIFECYCLE_ONLY_INIT')
end

function sysCall_sensing()
    -- Intentionally empty. Presence/lifecycle of the temporary simulation
    -- script is the only variable added relative to stepping-only.
end
