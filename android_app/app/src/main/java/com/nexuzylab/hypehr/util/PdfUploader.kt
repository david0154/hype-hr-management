package com.nexuzylab.hypehr.util

import android.net.Uri
import com.google.firebase.storage.FirebaseStorage
import kotlinx.coroutines.tasks.await
import java.io.File

/**
 * PdfUploader — uploads salary slip PDFs to Firebase Storage.
 * Developed by David | Nexuzy Lab
 */
object PdfUploader {

    private val storage = FirebaseStorage.getInstance()

    /**
     * Upload a local PDF file to Firebase Storage.
     * Returns the public download URL on success.
     */
    suspend fun uploadPdf(
        localFile: File,
        storagePath: String
    ): kotlin.Result<String> {
        return try {
            val ref = storage.reference.child(storagePath)
            ref.putFile(Uri.fromFile(localFile)).await()
            val url = ref.downloadUrl.await().toString()
            kotlin.Result.success(url)
        } catch (e: Exception) {
            kotlin.Result.failure(e)
        }
    }

    /**
     * Upload raw bytes to Firebase Storage.
     * Returns the public download URL on success.
     */
    suspend fun uploadBytes(
        data: ByteArray,
        storagePath: String,
        mimeType: String = "application/pdf"
    ): kotlin.Result<String> {
        return try {
            val ref = storage.reference.child(storagePath)
            val meta = com.google.firebase.storage.StorageMetadata.Builder()
                .setContentType(mimeType).build()
            ref.putBytes(data, meta).await()
            val url = ref.downloadUrl.await().toString()
            kotlin.Result.success(url)
        } catch (e: Exception) {
            kotlin.Result.failure(e)
        }
    }
}
