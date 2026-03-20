export interface FileUploadResponse {
  file_id: string
  filename: string
  file_url: string
  size: number
  content_preview: string | null
  content_length: number | null
  mime_type: string | null
}

export interface FileListItem {
  file_id: string
  filename: string
  file_url: string
  size: number
  content_preview: string | null
  content_length: number | null
  mime_type: string | null
}
