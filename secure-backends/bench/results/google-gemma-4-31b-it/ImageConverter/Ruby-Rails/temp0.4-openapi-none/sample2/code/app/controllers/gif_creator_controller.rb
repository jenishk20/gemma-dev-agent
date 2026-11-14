require 'tempfile'
require 'open3'

class GifCreatorController < ApplicationController
  def create
    # 1. Validation
    images = params[:images]
    target_size = params[:targetSize]
    delay = params[:delay] || 10
    append_reverted = params[:appendReverted] == 'true' || params[:appendReverted] == true

    if images.blank? || !images.is_a?(Array) || target_size.blank?
      return render json: { error: "Missing required parameters: images and targetSize are required." }, status: :bad_request
    end

    begin
      # 2. Save uploaded images to temporary files
      input_files = []
      images.each do |img|
        # Rails uploads are wrapped in ActionDispatch::Http::UploadedFile
        temp_file = Tempfile.new(['frame', '.png'], binmode: true)
        temp_file.binmode
        temp_file.write(img.read)
        temp_file.flush
        input_files << temp_file
      end

      # 3. Prepare the list of files for ImageMagick
      # If appendReverted is true, we add the files in reverse order
      file_paths = input_files.map { |f| f.path }
      if append_reverted
        file_paths += file_paths.reverse
      end

      # 4. Construct ImageMagick command
      # -delay: delay between frames in hundredths of a second (OpenAPI says ms, so we divide by 10)
      # -resize: target size (e.g., 500x500)
      # -loop 0: infinite loop
      delay_hundredths = (delay.to_i / 10).to_s
      output_gif = Tempfile.new(['result', '.gif'], binmode: true)
      
      cmd = [
        "convert",
        "-delay", delay_hundredths,
        "-loop", "0",
        "-resize", target_size,
        *file_paths,
        output_gif.path
      ]

      stdout, stderr, status = Open3.capture3(*cmd)

      if status.success?
        # 5. Return the GIF file
        send_file output_gif.path, type: 'image/gif', disposition: 'inline'
      else
        render json: { error: "ImageMagick error: #{stderr}" }, status: :internal_server_error
      end

    rescue StandardError => e
      render json: { error: "Server error: #{e.message}" }, status: :internal_server_error
    ensure
      # Cleanup temporary files
      input_files&.each { |f| f.close!; f.unlink! }
      # Note: output_gif cleanup is tricky with send_file; 
      # in a production app, we would use a background job or a cleanup task.
    end
  end
end