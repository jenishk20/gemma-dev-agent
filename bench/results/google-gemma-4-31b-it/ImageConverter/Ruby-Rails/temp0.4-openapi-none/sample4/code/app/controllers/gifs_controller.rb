require 'tempfile'
require 'open3'

class GifsController < ApplicationController
  def create
    images = params[:images]
    target_size = params[:target_size] || params[:targetSize]
    delay = params[:delay] || 10
    append_reverted = params[:appendReverted] == 'true'

    if images.blank? || target_size.blank?
      return render json: { error: "images and targetSize are required" }, status: :bad_request
    end

    unless images.is_a?(Array)
      return render json: { error: "images must be an array of files" }, status: :bad_request
    end

    begin
      # Create a temporary directory for this request
      Dir.mktmpdir do |dir|
        input_files = []
        
        # Save uploaded files to temp disk
        images.each_with_index do |img, index|
          temp_file = Tempfile.new(["frame_#{index}", ".jpg"], dir)
          temp_file.binmode
          temp_file.write(img.read)
          temp_file.close
          input_files << temp_file.path
        end

        # Handle the "appendReverted" logic
        if append_reverted
          # Duplicate the list of files in reverse order (excluding the last frame to avoid double frame)
          reverted_files = input_files[0...-1].reverse
          input_files += reverted_files
        end

        output_gif = File.join(dir, "result.gif")
        
        # Build ImageMagick command
        # -delay: time between frames (1/100th of a second)
        # -resize: target size (e.g., 500x500)
        # -loop 0: infinite loop
        delay_hundredths = (delay.to_i / 10).to_s # Convert ms to 1/100s
        
        cmd = [
          "convert",
          "-delay", delay_hundredths,
          "-resize", target_size,
          *input_files,
          "-loop", "0",
          output_gif
        ]

        stdout, stderr, status = Open3.capture3(*cmd)

        if status.success?
          send_file output_gif, type: 'image/gif', disposition: 'inline'
        else
          render json: { error: "ImageMagick error: #{stderr}" }, status: :internal_server_error
        end
      end
    rescue StandardError => e
      render json: { error: "Server Error: #{e.message}" }, status: :internal_server_error
    end
  end
end