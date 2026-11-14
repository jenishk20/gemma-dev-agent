require 'open3'
require 'fileutils'

class FramesController < ApplicationController
  def extract
    video_file = params[:video]
    frame_number = params[:frameNumber].to_i
    
    if video_file.nil? || frame_number <= 0
      return render json: { error: "Invalid input. Please provide a video and a valid frame number." }, status: :bad_request
    end

    # Create a unique temporary directory for this request
    tmp_dir = Rails.root.join('tmp', "extract_#{SecureRandom.hex(8)}")
    FileUtils.mkdir_p(tmp_dir)

    begin
      # Save the uploaded video to disk
      video_path = tmp_dir.join("input_video")
      File.open(video_path, 'wb') do |file|
        file.write(video_file.read)
      end

      output_path = tmp_dir.join("frame.png")

      # ffmpeg command: 
      # -i input: input file
      # -vf "select=eq(n,FRAME_INDEX)": select the specific frame index
      # -vframes 1: output exactly one frame
      # -f image2: output format as image
      cmd = [
        "ffmpeg", 
        "-i", video_path.to_s, 
        "-vf", "select=eq(n,#{frame_number})", 
        "-vframes", "1", 
        "-f", "image2", 
        output_path.to_s
      ]

      stdout, stderr, status = Open3.capture3(*cmd)

      if status.success? && File.exist?(output_path)
        # Send the image file and then clean up the tmp directory
        # We use a block with send_file or a custom response to ensure cleanup
        # Since send_file is asynchronous in some servers, we use a simple approach:
        # In a production app, we'd use a background job or a tempfile with an auto-delete.
        # For this task, we send the file.
        
        # To ensure the file is deleted after sending, we can read it into memory 
        # since a single frame is small.
        image_data = File.read(output_path)
        
        # Cleanup before sending response
        FileUtils.rm_rf(tmp_dir)
        
        send_data image_data, type: 'image/png', disposition: 'inline'
      else
        FileUtils.rm_rf(tmp_dir)
        render json: { error: "Frame at index #{frame_number} could not be found." }, status: :not_found
      end
    rescue StandardError => e
      FileUtils.rm_rf(tmp_dir)
      render json: { error: "Server error: #{e.message}" }, status: :internal_server_error
    end
  end
end