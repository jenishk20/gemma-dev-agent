require 'open3'
require 'fileutils'

class FramesController < ApplicationController
  def extract
    video_file = params[:video]
    frame_number = params[:frameNumber].to_i
    
    if video_file.nil? || frame_number <= 0
      return render json: { error: "Invalid input parameters" }, status: :bad_request
    end

    # Create a temporary directory for processing
    tmp_dir = Rails.root.join('tmp', 'frame_extraction', SecureRandom.uuid)
    FileUtils.mkdir_p(tmp_dir)

    begin
      # Save the uploaded file to disk
      input_path = tmp_dir.join('input_video')
      File.open(input_path, 'wb') { |f| f.write(video_file.read) }

      output_path = tmp_dir.join('frame.png')

      # ffmpeg command: 
      # -i: input file
      # -vf "select='eq(n,FRAME_INDEX)'": filter to select the specific frame index
      # -vframes 1: output exactly one frame
      # -q:v 2: high quality
      cmd = "ffmpeg -i #{input_path} -vf \"select='eq(n,#{frame_number})'\" -vframes 1 -q:v 2 #{output_path}"
      
      stdout, stderr, status = Open3.capture3(cmd)

      if status.success? && File.exist?(output_path)
        send_file output_path, type: 'image/png', disposition: 'inline'
      else
        render json: { error: "Frame at index #{frame_number} could not be found." }, status: :not_found
      end
    rescue StandardError => e
      render json: { error: "Internal Server Error: #{e.message}" }, status: :internal_server_error
    ensure
      # Cleanup temporary files after the response is sent
      # Note: In a production app, we'd use a background job or a middleware to clean up 
      # because send_file happens after the controller action returns.
      # For this small app, we'll trigger a cleanup thread.
      Thread.new do
        sleep 5 # Give time for the file to be sent
        FileUtils.rm_rf(tmp_dir)
      end
    end
  end
end