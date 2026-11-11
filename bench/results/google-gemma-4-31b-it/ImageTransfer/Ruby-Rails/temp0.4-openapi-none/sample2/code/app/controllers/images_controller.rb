class ImagesController < ApplicationController
  # POST /upload
  def upload
    if params[:file].blank?
      return render json: { error: "No file uploaded" }, status: :bad_request
    end

    begin
      # We create a lightweight record to attach the file to.
      # Since we don't have a specific Image model defined in the prompt, 
      # we use ActiveStorage::Blob directly to handle the upload.
      blob = ActiveStorage::Blob.create_and_upload!(
        io: params[:file].tempfile,
        filename: params[:file].original_filename,
        content_type: params[:file].content_type,
        blob: ActiveStorage::Blob.generate_unique_secure_token
      )

      render json: { id: blob.key }, status: :ok
    rescue StandardError => e
      render json: { error: e.message }, status: :internal_server_error
    end
  end

  # GET /images/{imageId}
  def show
    blob = ActiveStorage::Blob.find_by(key: params[:imageId])

    if blob
      # download: false and disposition: 'inline' ensures the browser 
      # attempts to render the image rather than downloading it.
      send_data blob.download, 
                type: blob.content_type, 
                disposition: 'inline'
    else
      render json: { error: "Image not found" }, status: :not_found
    end
  rescue StandardError => e
    render json: { error: e.message }, status: :internal_server_error
  end
end