class ConverterController < ApplicationController
  def convert
    file = params[:file]

    if file.nil?
      return render json: { error: "Missing file parameter" }, status: :bad_request
    end

    unless file.content_type == 'application/pdf'
      return render json: { error: "Invalid file type. Please upload a PDF." }, status: :bad_request
    end

    begin
      # Save uploaded file to a temporary location
      uploaded_file = file.path
      
      # Use pdftotext utility. 
      # '-' tells pdftotext to output to stdout instead of a file.
      # We use Open3 or backticks to capture the output.
      text_content = `pdftotext "#{uploaded_file}" -`

      if text_content.nil? || text_content.empty?
        # If the command failed or PDF was empty/unreadable
        return render json: { error: "Conversion failed or PDF contains no extractable text" }, status: :internal_server_error
      end

      # Return plain text as per OpenAPI schema
      render plain: text_content, status: :ok
    rescue StandardError => e
      render json: { error: "Internal Server Error: #{e.message}" }, status: :internal_server_error
    end
  end
end