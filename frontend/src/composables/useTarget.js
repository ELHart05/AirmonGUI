import { ref } from 'vue'

// Cross-view shared target — set from ScanView, consumed by DeauthView/HandshakeView
const bssid = ref('')
const essid = ref('')
const channel = ref('')
const capFile = ref('')  // set from HandshakeView, consumed by CrackView
const authentication = ref('')  // raw auth field from airodump CSV
const pmf = ref('')  // 'required' | 'capable' | '' — derived from auth/privacy

function _derivePmf(privacy, auth) {
  const p = (privacy || '').toUpperCase()
  const a = (auth || '').toUpperCase()
  // WPA3-SAE / OWE always mandate PMF
  if (a.includes('SAE') || a.includes('OWE') || p.includes('WPA3')) return 'required'
  // 802.11w MFP: airodump-ng shows "MGMT" in the auth column when PMF is negotiated
  if (a.includes('MGMT') || a.includes('MFP')) return 'capable'
  return ''
}

export function useTarget() {
  function setTarget(network) {
    bssid.value = _pick(network, ['BSSID', 'bssid']) || ''
    essid.value = _pick(network, ['ESSID', 'essid']) || ''
    channel.value = _pick(network, ['channel', 'Channel', ' channel']) || ''
    const auth = _pick(network, ['Authentication', 'authentication', 'Auth'])
    const priv = _pick(network, ['Privacy', 'privacy'])
    authentication.value = auth
    pmf.value = _derivePmf(priv, auth)
  }

  function setCrackFile(path) {
    capFile.value = path || ''
  }

  function clear() {
    bssid.value = ''
    essid.value = ''
    channel.value = ''
    capFile.value = ''
    authentication.value = ''
    pmf.value = ''
  }

  return { bssid, essid, channel, capFile, authentication, pmf, setTarget, setCrackFile, clear }
}

function _pick(obj, keys) {
  for (const key of keys) {
    const val = obj[key]
    if (val && String(val).trim()) return String(val).trim()
  }
  return ''
}
