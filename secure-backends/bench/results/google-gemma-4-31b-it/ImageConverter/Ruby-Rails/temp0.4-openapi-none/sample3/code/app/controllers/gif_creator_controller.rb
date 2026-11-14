require 'open3'
require 'tempfile'

class GifCreatorController < ApplicationController
  def create
    images = params[:images]
    target_size = params[:target_size] || params[:targetSize]
    delay = params[:delay] || 10
    append_reverted = params[:appendReverted] == 'true'

    if images.blank? || target_size.blank?
      return render json: { error: "Missing required parameters: images and targetSize" }, status: :bad_request
    end

    unless images.is_a?(Array)
      return render json: { error: "images must be an array of files" }, status: :bad_request
    end

    begin
      # Create temporary directory for processing
      Dir.mktmpdir do |dir|
        input_files = []
        
        # Save uploaded files to disk
        images.each_with_index do |img, index|
          temp_file = Tempfile.new(["frame_#{index}", ".png"], dir)
          temp_file.binmode
          temp_file.write(img.read)
          temp_file.close
          input_files << temp_file.path
        end

        # Handle appendReverted logic
        if append_reverted
          # Create a reversed list of the same files
          input_files += input_files.reverse[0...-1] # avoid duplicating the last frame twice
        end

        output_path = File.join(dir, "result.gif")
        
        # Build ImageMagick command
        # -delay: time between frames in hundredths of a second (10ms = 0.1, 100ms = 1.0)
        # convert_delay = delay / 10
        convert_delay = (delay.to_f / 10).to_s
        
        # Command: convert -delay X -resize WxH image1 image2 ... result.gif
        cmd = [
          "convert",
          "-delay", convert_delay,
          "-resize", target_size,
          *input_files,
          output_path
        ]

        stdout, stderr, status = Open3.capture3(*cmd)

        if status.success?
          send_file output_path, type: 'image/gif', disposition: 'inline'
        else
          render json: { error: "ImageMagick error: #{stderr}" }, status: :internal_server_error
        end
      end
    rescue StandardError => e
      render json: { error: "Server error: #{e.message}" }, status: :internal_server_error
    end
  end
end