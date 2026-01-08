package com.example.gibberlink

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class ChatAdapter(private val messages: MutableList<ChatMessage>) :
    RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private val VIEW_TYPE_SENT = 1
    private val VIEW_TYPE_RECEIVED = 2

    class SentViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val textMessage: TextView = itemView.findViewById(R.id.textMessage)
    }

    class ReceivedViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val textMessage: TextView = itemView.findViewById(R.id.textMessage)
        // Name view removed to match new UI design
    }

    override fun getItemViewType(position: Int): Int {
        return if (messages[position].isSent) VIEW_TYPE_SENT else VIEW_TYPE_RECEIVED
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        return if (viewType == VIEW_TYPE_SENT) {
            val view = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_message_sent, parent, false)
            SentViewHolder(view)
        } else {
            val view = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_message_received, parent, false)
            ReceivedViewHolder(view)
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = messages[position]

        if (holder is SentViewHolder) {
            holder.textMessage.text = message.message
        } else if (holder is ReceivedViewHolder) {
            // Include name in the message text or just show message?
            // For now, adhering strictly to UI: just message. 
            // If user wants name, we can prepend it: "${message.name}: \n${message.message}"
            holder.textMessage.text = "${message.name}:\n${message.message}" 
        }
    }

    override fun getItemCount(): Int {
        return messages.size
    }

    fun addMessage(message: ChatMessage) {
        messages.add(message)
        notifyItemInserted(messages.size - 1)
    }
}
