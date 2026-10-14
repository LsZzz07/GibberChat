package com.example.gibberlink

import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.ViewTreeObserver
import android.view.animation.AccelerateDecelerateInterpolator
import android.view.animation.OvershootInterpolator
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.DefaultItemAnimator
import androidx.recyclerview.widget.RecyclerView

/**
 * Send / receive animations for the chat screen.
 *
 * - Sent messages slide in from the right with a small bounce, the send button
 *   squishes, and the status line switches to "Transmitting...".
 * - Received messages slide in from the left and the status line switches to
 *   "Receiving...".
 * - The wave icon pulses all the time and speeds up while busy.
 *
 * Needs no changes to ChatAdapter: it listens for notifyItemInserted().
 */
class ChatAnimator(
    private val recycler: RecyclerView,
    private val wave: ImageView,
    private val status: TextView,
    private val sendButton: View
) {
    private val handler = Handler(Looper.getMainLooper())
    private val cyan = Color.parseColor("#22D3EE")
    private val violet = Color.parseColor("#A78BFA")
    private var waveAnim: ObjectAnimator? = null
    private var observing = false

    private val toIdle = Runnable { setBusy(false, "Listening for sound") }

    private val observer = object : RecyclerView.AdapterDataObserver() {
        override fun onItemRangeInserted(positionStart: Int, itemCount: Int) {
            runAfterLayout { onInserted(positionStart, itemCount) }
        }
    }

    /** Call once, AFTER recyclerChat.adapter has been set. */
    fun start() {
        // Turn off RecyclerView's own fade-in so it doesn't fight ours.
        recycler.itemAnimator = object : DefaultItemAnimator() {
            override fun animateAdd(holder: RecyclerView.ViewHolder): Boolean {
                dispatchAddFinished(holder)
                return false
            }
        }
        recycler.adapter?.let {
            it.registerAdapterDataObserver(observer)
            observing = true
        }
        startWave(900L)
    }

    /** Call from onDestroy(). */
    fun stop() {
        if (observing) {
            try {
                recycler.adapter?.unregisterAdapterDataObserver(observer)
            } catch (_: IllegalStateException) {
            }
            observing = false
        }
        waveAnim?.cancel()
        handler.removeCallbacksAndMessages(null)
    }

    private fun runAfterLayout(block: () -> Unit) {
        val vto = recycler.viewTreeObserver
        if (!vto.isAlive) return
        vto.addOnPreDrawListener(object : ViewTreeObserver.OnPreDrawListener {
            override fun onPreDraw(): Boolean {
                val current = recycler.viewTreeObserver
                if (current.isAlive) current.removeOnPreDrawListener(this)
                block()
                return true
            }
        })
    }

    private fun onInserted(start: Int, count: Int) {
        for (pos in start until start + count) {
            val holder = recycler.findViewHolderForAdapterPosition(pos) ?: continue
            val mine = holder.itemViewType == VIEW_TYPE_SENT
            animateIn(holder.itemView, mine)
            if (mine) {
                pulseSend()
                setBusy(true, "Transmitting...", 1200L)
            } else {
                setBusy(true, "Receiving...", 1100L)
            }
        }
        recycler.smoothScrollToPosition(start + count - 1)
    }

    private fun animateIn(v: View, mine: Boolean) {
        val density = recycler.resources.displayMetrics.density
        v.pivotX = if (mine) v.width.toFloat() else 0f
        v.pivotY = v.height.toFloat()
        v.alpha = 0f
        v.translationX = (if (mine) 56f else -56f) * density
        v.scaleX = 0.9f
        v.scaleY = 0.9f
        ObjectAnimator.ofFloat(v, View.ALPHA, 0f, 1f).setDuration(220L).start()
        v.animate()
            .translationX(0f)
            .scaleX(1f)
            .scaleY(1f)
            .setDuration(420L)
            .setInterpolator(OvershootInterpolator(1.1f))
            .start()
    }

    private fun pulseSend() {
        sendButton.animate()
            .scaleX(0.78f)
            .scaleY(0.78f)
            .setDuration(80L)
            .withEndAction {
                sendButton.animate()
                    .scaleX(1f)
                    .scaleY(1f)
                    .setDuration(300L)
                    .setInterpolator(OvershootInterpolator(3f))
                    .start()
            }
            .start()
    }

    private fun setBusy(busy: Boolean, text: String, resetAfterMs: Long = 0L) {
        handler.removeCallbacks(toIdle)
        status.text = text
        val color = if (busy) violet else cyan
        status.setTextColor(color)
        wave.setColorFilter(color)
        startWave(if (busy) 380L else 900L)
        if (busy && resetAfterMs > 0L) handler.postDelayed(toIdle, resetAfterMs)
    }

    private fun startWave(periodMs: Long) {
        waveAnim?.cancel()
        wave.scaleY = 1f
        waveAnim = ObjectAnimator.ofFloat(wave, View.SCALE_Y, 0.45f, 1.15f).apply {
            duration = periodMs
            repeatCount = ValueAnimator.INFINITE
            repeatMode = ValueAnimator.REVERSE
            interpolator = AccelerateDecelerateInterpolator()
            start()
        }
    }

    private companion object {
        const val VIEW_TYPE_SENT = 1
    }
}
