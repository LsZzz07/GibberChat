package com.example.gibberlink

class GGWave {

    companion object {
        init {
            System.loadLibrary("gibberlink")
        }
    }

    private var instanceId: Long = -1

    fun init() {
        instanceId = nativeInit()
    }

    fun free() {
        if (instanceId != -1L) {
            nativeFree(instanceId)
            instanceId = -1
        }
    }

    fun process(data: ByteArray, len: Int): String? {
        if (instanceId == -1L) return null
        val result = nativeProcess(instanceId, data, len)
        return result?.let { String(it, Charsets.UTF_8) }
    }

    fun encode(message: String, protocolId: Int): ByteArray? {
        if (instanceId == -1L) return null
        return nativeEncode(instanceId, message, protocolId)
    }

    private external fun nativeInit(): Long
    private external fun nativeFree(id: Long)
    private external fun nativeProcess(id: Long, data: ByteArray, len: Int): ByteArray?
    private external fun nativeEncode(id: Long, message: String, protocolId: Int): ByteArray?
}

