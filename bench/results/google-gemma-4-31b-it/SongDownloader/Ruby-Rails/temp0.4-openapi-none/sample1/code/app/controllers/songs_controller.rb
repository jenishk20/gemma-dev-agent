class SongsController < ApplicationController
  def download
    filename = params[:filename]

    if filename.blank?
      return render json: { error: "Invalid input: filename is required" }, status: :bad_request
    end

    # Security: Prevent directory traversal by ensuring the filename 
    # does not contain path separators or ".."
    if filename.include?('/') || filename.include?('\\') || filename.include?('..')
      return render json: { error: "Invalid input: illegal characters in filename" }, status: :bad_request
    end

    song_path = File.join('/var/songs', filename)

    if File.exist?(song_path) && File.file?(song_path)
      # send_file handles streaming the content efficiently
      # We set the content type to audio/mpeg as per OpenAPI spec
      send_file song_path, type: 'audio/mpeg', disposition: 'inline'
    else
      render json: { error: "File does not exist" }, status: :not_found
    end
  end
end