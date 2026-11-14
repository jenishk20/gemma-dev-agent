require 'tempfile'
require 'open3'

class GifsController < ApplicationController
  def create
    # Validate required parameters
    images = params[:images]
    target_size = params[:targetSize]
    delay = params[:delay] || 10
    append_reverted = params[:appendReverted] == 'true'

    if images.blank? || target_size.blank?
      return render json: { error: "Missing required parameters: images and targetSize are required." }, status: :bad_request
    end

    unless images.is_a?(Array)
      return render json: { error: "images must be an array of files." }, status: :bad_request
    end

    begin
      # Create a temporary directory to store uploaded frames
      Dir.mktmpdir do |dir|
        input_files = []
        
        # Save uploaded files to disk
        images.each_with_index do |img, index|
          # Rails uploads are typically ActionDispatch::Http::UploadedFile
          temp_path = File.join(dir, "frame_#{index}.png")
          File.open(temp_path, 'wb') { |f| f.write(img.read) }
          input_files << temp_path
        end

        # Handle "appendReverted" logic
        if append_reverted
          reversed_files = input_files.reverse
          reversed_files.each_with_index do |file, index|
            # Create a copy to ensure we have distinct paths for the command line
            rev_path = File.join(dir, "rev_#{index}.png")
            FileUtils.cp(file, rev_path)
            input_files << rev_path
          end
        end

        # Prepare output path
        output_gif = File.join(dir, "result.gif")

        # Construct ImageMagick command
        # -delay: time between frames in 1/100ths of a second. 
        # The API specifies delay in milliseconds. ImageMagick -delay is in ticks (1 tick = 10ms).
        # So delay_ms / 10.
        im_delay = (delay.to_i / 10).to_s
        
        # Command: convert -delay [ticks] -resize [size] [inputs] [output]
        # We use shelljoin to prevent command injection
        cmd = [
          "convert",
          "-delay", im_delay,
          "-resize", target_size,
          *input_files,
          output_gif
        ]

        stdout, stderr, status = Open3.capture3(*cmd)

        if status.success?
          # Send the resulting GIF file
          send_file output_gif, type: 'image/gif', disposition: 'inline'
        else
          Rails.logger.error("ImageMagick Error: #{stderr}")
          render json: { error: "Failed to process GIF: #{stderr}" }, status: :internal_server_error
        end
      end
    rescue StandardError => e
      Rails.logger.error("Server Error: #{e.message}")
      render json: { error: "Internal Server Error: #{e.message}" }, status: :internal_server_error
    end
  end
end