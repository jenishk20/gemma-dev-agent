require 'tempfile'
require 'shellwords'

class GifCreatorController < ApplicationController
  def create
    images = params[:images]
    target_size = params[:target_size] || params[:targetSize]
    delay = params[:delay] || 10
    append_reverted = params[:appendReverted] == 'true' || params[:append_reverted] == 'true'

    if images.blank? || target_size.blank?
      return render json: { error: "Missing required parameters: images and targetSize" }, status: :bad_request
    end

    unless images.is_a?(Array)
      return render json: { error: "images must be an array of files" }, status: :bad_request
    end

    begin
      # Create a temporary directory for processing
      Dir.mktmpdir do |dir|
        input_files = []
        
        # Save uploaded files to disk
        images.each_with_index do |img, index|
          temp_file = Tempfile.new(["frame_#{index}", ".img"], dir)
          temp_file.binmode
          temp_file.write(img.read)
          temp_file.flush
          input_files << temp_file.path
        end

        # Handle the "appendReverted" logic (boomerang effect)
        if append_reverted && input_files.size > 1
          # Add files in reverse order, excluding the first and last to avoid duplicates at the pivot
          reverted = input_files[1...-1].reverse
          # To actually use 'convert', we need physical files or a list. 
          # Since we can't easily create new tempfiles for the reverse without duplicating data,
          # we will just pass the paths twice to the convert command.
          processing_list = input_files + reverted
        else
          processing_list = input_files
        end

        output_gif = File.join(dir, "result.gif")
        
        # Construct ImageMagick command
        # -delay: time between frames (1/100ths of a second)
        # -resize: target size (e.g., 500x500)
        # -loop 0: infinite loop
        
        # Convert delay from ms to 1/100s
        im_delay = (delay.to_i / 10).to_s
        
        # Escape paths to prevent shell injection
        escaped_inputs = processing_list.map { |f| Shellwords.escape(f) }.join(' ')
        escaped_output = Shellwords.escape(output_gif)
        escaped_size = Shellwords.escape(target_size)

        cmd = "convert -delay #{im_delay} -loop 0 #{escaped_inputs} -resize #{escaped_size} #{escaped_output}"
        
        if system(cmd)
          send_file output_gif, type: 'image/gif', disposition: 'inline'
        else
          render json: { error: "ImageMagick conversion failed" }, status: :internal_server_error
        end
      end
    rescue StandardError => e
      render json: { error: e.message }, status: :internal_server_error
    end
  end
end