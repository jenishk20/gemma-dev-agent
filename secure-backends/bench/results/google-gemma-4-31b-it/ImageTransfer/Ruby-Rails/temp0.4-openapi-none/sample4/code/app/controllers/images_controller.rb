class ImagesController < ApplicationController
  # POST /upload
  def upload
    if params[:file].present?
      @image = Image.create(file: params[:file])
      
      if @image.persisted?
        render json: { id: @image.id }, status: :ok
      else
        render json: { error: "Could not save image" }, status: :bad_request
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
      # We use send_data to ensure the browser renders the image inline 
      # instead of forcing a download.
      send_data @image.file.download, 
                type: @image.file.content_type, 
                disposition: 'inline'
    else
      render json: { error: "Image not found" }, status: :not_found
    end
  rescue StandardError => e
    render json: { error: e.message }, status: :internal_server_error
  end
end