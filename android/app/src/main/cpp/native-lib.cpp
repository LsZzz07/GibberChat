#include <jni.h>
#include <string>
#include <vector>
#include <android/log.h>

// Forward declaration of ggwave functions if header isn't present during this generation step
// Ideally user includes "ggwave.h"
// #include "ggwave.h"

// Since I cannot write ggwave.h, I will assume it is included and user has it.
// I will write the JNI bindings assuming the standard ggwave API.

#include "ggwave/ggwave.h"


#define LOG_TAG "GibberlinkNative"
#define LOGD(...) __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

extern "C" {

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_gibberlink_GGWave_nativeInit(
        JNIEnv* env,
        jobject /* this */) {
    ggwave_Parameters parameters = ggwave_getDefaultParameters();
    parameters.sampleRateInp = 48000;
    parameters.sampleRateOut = 48000;
    parameters.sampleFormatInp = GGWAVE_SAMPLE_FORMAT_I16;
    parameters.sampleFormatOut = GGWAVE_SAMPLE_FORMAT_I16;
    
    // Create instance
    ggwave_Instance instanceId = ggwave_init(parameters);
    LOGD("nativeInit usage: instanceId=%d", instanceId);
    return (jlong) instanceId;
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_gibberlink_GGWave_nativeFree(
        JNIEnv* env,
        jobject /* this */,
        jlong instanceId) {
    LOGD("nativeFree: instanceId=%ld", (long)instanceId);
    ggwave_free((ggwave_Instance) instanceId);
}

extern "C" JNIEXPORT jint JNICALL
Java_com_example_gibberlink_GGWave_nativeDecode(
        JNIEnv* env,
        jobject /* this */,
        jlong instanceId,
        jbyteArray dataBytes,
        jint dataLen,
        jobject outputBuffer) {
            
    // Placeholder - not used by current logic, but kept for safety
    return 0; 
}

extern "C" JNIEXPORT jbyteArray JNICALL
Java_com_example_gibberlink_GGWave_nativeProcess(
        JNIEnv* env,
        jobject /* this */,
        jlong instanceId,
        jbyteArray inputData,
        jint length) {
            
    jboolean isCopy;
    jbyte* data = env->GetByteArrayElements(inputData, &isCopy);

    // Decode attempt
    char output[256];
    int ret = ggwave_decode((ggwave_Instance)instanceId, (char*)data, length, output);

    env->ReleaseByteArrayElements(inputData, data, 0);

    if (ret > 0) {
        LOGD("nativeProcess: Decoded %d bytes: %s", ret, output);
        jbyteArray result = env->NewByteArray(ret);
        env->SetByteArrayRegion(result, 0, ret, (jbyte*)output);
        return result;
    }

    return NULL;
}

extern "C" JNIEXPORT jbyteArray JNICALL
Java_com_example_gibberlink_GGWave_nativeEncode(
        JNIEnv* env,
        jobject /* this */,
        jlong instanceId,
        jstring message,
        jint protocolId) {

    const char *text = env->GetStringUTFChars(message, 0);
    int len = env->GetStringUTFLength(message);
    
    LOGD("nativeEncode: instanceId=%ld, len=%d, protocolId=%d, text=%s", (long)instanceId, len, protocolId, text);

    // Query size
    int n = ggwave_encode((ggwave_Instance)instanceId, text, len, (ggwave_ProtocolId)protocolId, 50, NULL, 1);
    
    LOGD("nativeEncode: Query size n=%d", n);

    if (n > 0) {
        std::vector<char> buffer(n);
        int finalSize = ggwave_encode((ggwave_Instance)instanceId, text, len, (ggwave_ProtocolId)protocolId, 50, buffer.data(), 0);
        LOGD("nativeEncode: Final encoded size=%d", finalSize);
        
        jbyteArray result = env->NewByteArray(n);
        env->SetByteArrayRegion(result, 0, n, (jbyte*)buffer.data());
        env->ReleaseStringUTFChars(message, text);
        return result;
    } else {
        LOGE("nativeEncode failure: n=%d", n);
    }
    
    env->ReleaseStringUTFChars(message, text);
    return NULL; 
}
} // extern "C"
