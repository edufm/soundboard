// Module-level singleton: one AudioContext, one effects chain, shared by
// every sound button. Effects are toggled globally, not per-clip.

let ctx = null
let chain = null
let speed = 1 // playback rate multiplier, applied to clips started after a change
const bufferCache = new Map() // path -> Promise<AudioBuffer>
const activeSources = new Set()

function makeDistortionCurve(amount) {
  const samples = 44100
  const curve = new Float32Array(samples)
  const deg = Math.PI / 180
  for (let i = 0; i < samples; i++) {
    const x = (i * 2) / samples - 1
    curve[i] = ((3 + amount) * x * 20 * deg) / (Math.PI + amount * Math.abs(x))
  }
  return curve
}

function generateImpulseResponse(audioCtx, durationSec, decay) {
  const rate = audioCtx.sampleRate
  const length = rate * durationSec
  const impulse = audioCtx.createBuffer(2, length, rate)
  for (let channel = 0; channel < 2; channel++) {
    const data = impulse.getChannelData(channel)
    for (let i = 0; i < length; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, decay)
    }
  }
  return impulse
}

// A "stage" is a wet/dry parallel pair: input fans out to the effect node
// (-> wetGain) and straight to dryGain, both summing into the stage's output.
// Toggling only ramps gains, so live nodes are never connected/disconnected
// (avoids clicks/pops).
function buildStage(audioCtx, effectNode) {
  const stageIn = audioCtx.createGain()
  const stageOut = audioCtx.createGain()
  const wetGain = audioCtx.createGain()
  const dryGain = audioCtx.createGain()

  wetGain.gain.value = 0
  dryGain.gain.value = 1

  stageIn.connect(effectNode)
  effectNode.connect(wetGain)
  wetGain.connect(stageOut)

  stageIn.connect(dryGain)
  dryGain.connect(stageOut)

  return { stageIn, stageOut, wetGain, dryGain }
}

function initChain(audioCtx) {
  const distortionNode = audioCtx.createWaveShaper()
  distortionNode.curve = makeDistortionCurve(400)
  distortionNode.oversample = '4x'
  const distortionStage = buildStage(audioCtx, distortionNode)

  const delayNode = audioCtx.createDelay(1.0)
  delayNode.delayTime.value = 0.3
  const feedbackGain = audioCtx.createGain()
  feedbackGain.gain.value = 0.35
  delayNode.connect(feedbackGain)
  feedbackGain.connect(delayNode)
  const echoStage = buildStage(audioCtx, delayNode)

  const convolverNode = audioCtx.createConvolver()
  convolverNode.buffer = generateImpulseResponse(audioCtx, 2, 2)
  const reverbStage = buildStage(audioCtx, convolverNode)

  const masterGain = audioCtx.createGain()
  masterGain.gain.value = 0.9

  distortionStage.stageOut.connect(echoStage.stageIn)
  echoStage.stageOut.connect(reverbStage.stageIn)
  reverbStage.stageOut.connect(masterGain)
  masterGain.connect(audioCtx.destination)

  return {
    firstStageIn: distortionStage.stageIn,
    masterGain,
    stages: {
      distortion: distortionStage,
      echo: echoStage,
      reverb: reverbStage,
    },
  }
}

function getContext() {
  if (!ctx) {
    ctx = new AudioContext()
    chain = initChain(ctx)
  }
  return ctx
}

// intensity is a continuous 0..1 wet/dry mix, driven by the effects bar sliders.
export function setEffect(name, intensity) {
  const c = getContext()
  const stage = chain.stages[name]
  if (!stage) return
  const wet = Math.min(1, Math.max(0, intensity))
  stage.wetGain.gain.setTargetAtTime(wet, c.currentTime, 0.02)
  stage.dryGain.gain.setTargetAtTime(1 - wet, c.currentTime, 0.02)
}

export function setSpeed(value) {
  speed = value
  const c = getContext()
  for (const source of activeSources) {
    source.playbackRate.setTargetAtTime(value, c.currentTime, 0.02)
  }
}

export function setVolume(value) {
  const c = getContext()
  chain.masterGain.gain.setTargetAtTime(value, c.currentTime, 0.02)
}

// Escapes each path segment so filenames containing URL-reserved characters
// (e.g. "Como é Amigo?.mp3") don't get misparsed as query strings/fragments.
function encodePath(path) {
  return path.split('/').map(encodeURIComponent).join('/')
}

function loadBuffer(path) {
  if (bufferCache.has(path)) return bufferCache.get(path)

  const c = getContext()
  const promise = fetch(encodePath(path))
    .then((res) => {
      if (!res.ok) throw new Error(`${path}: ${res.status}`)
      return res.arrayBuffer()
    })
    .then((arrayBuffer) => c.decodeAudioData(arrayBuffer))
    .catch((err) => {
      bufferCache.delete(path)
      throw err
    })

  bufferCache.set(path, promise)
  return promise
}

export async function playClip({ path, startTime, endTime, gainDb = 0 }) {
  const c = getContext()
  if (c.state === 'suspended') await c.resume()

  const buffer = await loadBuffer(path)
  const duration = Math.max(0, endTime - startTime)

  const source = c.createBufferSource()
  source.buffer = buffer
  source.playbackRate.value = speed

  // Per-clip loudness correction (see tools/measure_loudness.py) — cheap:
  // just a gain multiplier baked into the graph, no extra processing cost.
  const clipGain = c.createGain()
  clipGain.gain.value = 10 ** (gainDb / 20)

  source.connect(clipGain)
  clipGain.connect(chain.firstStageIn)
  source.addEventListener('ended', () => activeSources.delete(source))
  activeSources.add(source)
  source.start(c.currentTime, startTime, duration)
}

export function stopAll() {
  for (const source of activeSources) {
    try {
      source.stop()
    } catch {
      // already stopped
    }
  }
  activeSources.clear()
}
