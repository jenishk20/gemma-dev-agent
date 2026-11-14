class ImagesController < ApplicationController
  def upload
    begin
      # The OpenAPI schema expects a field named 'file'
      uploaded_file = params[:file]

      if uploaded_file.blank?
        return render json: { error: "No file uploaded" }, status: :bad_request
      end

      image = Image.create!(file: uploaded_file)
      
      render json: { id: image.id.to_s }, status: :ok
    rescue ActiveRecord::RecordInvalid => e
      render json: { error: e.message }, status: :bad_request
    rescue StandardError => e
      render json: { error: "Internal server error: #{e.message}" }, status: :internal_server_error
    end
  end

  def show
    image = Image.find_by(id: params[:imageId])

    if image && image.file.attached?
      # We use send_data with disposition: 'inline' to ensure the browser 
      # attempts to render the image rather than downloading it.
      # ActiveStorage's download method provides the binary data and content type.
      image.file.open do |file|
        send_data File.read(file), 
                  type: image.file.content_type, 
                  disposition: 'inline'
      end
    else
      render json: { error: "Image not found" }, status: :not_found
    end
  rescue StandardError => e
    render json: { error: "Internal server error: #{e.message}" }, status: :internal_server_error
  end
end