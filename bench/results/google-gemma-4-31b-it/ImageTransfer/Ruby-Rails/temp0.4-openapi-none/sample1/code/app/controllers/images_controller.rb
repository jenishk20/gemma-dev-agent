class ImagesController < ApplicationController
  # POST /upload
  def create
    if params[:file].present?
      @image = Image.new(file: params[:file])
      
      if @image.save
        render json: { id: @image.id }, status: :ok
      else
        render json: { error: "Failed to save image" }, status: :bad_request
      end
    else
      render json: { error: "No file uploaded" }, status: :bad_request
    end
  rescue StandardError => e
    render json: { error: e.message }, status: :internal_server_error
  end

  # GET /images/{imageId}
  def show
    @image = Image.find_by(id: params[:imageId])

    if @image && @image.file.attached?
      # send_data is used to stream the file. 
      # disposition: 'inline' ensures the browser tries to display it rather than download it.
      # content_type is preserved from the original upload.
      send_data @image.file.download, 
                filename: @image.file.filename.to_s, 
                content_type: @image.file.content_type, 
                disposition: 'inline'
    else
      render json: { error: "Image not found" }, status: :not_found
    end
  rescue StandardError => e
    render json: { error: e.message }, status: :internal_server_error
  end
end