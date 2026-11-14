class SearchController < ApplicationController
  def index
    regex_param = params[:regex]
    directory_param = params[:directory] || ""
    recursive_param = params[:recursive] == 'true'

    if regex_param.blank?
      return render json: { error: "regex parameter is required" }, status: :bad_request
    end

    begin
      # Validate and compile regex
      regex = Regexp.new(regex_param)
    rescue RegexpError => e
      return render json: { error: "Invalid regex pattern: #{e.message}" }, status: :bad_request
    end

    # Define root files directory
    root_path = Rails.root.join('files')
    
    # Sanitize and resolve target directory to prevent directory traversal
    target_dir = File.expand_path(File.join(root_path, directory_param))
    
    unless target_dir.start_with?(root_path.to_s) && Dir.exist?(target_dir)
      return render json: { error: "Invalid or inaccessible directory" }, status: :bad_request
    end

    matching_files = []
    
    # Determine search pattern
    pattern = recursive_param ? File.join(target_dir, "**", "*") : File.join(target_dir, "*")

    begin
      Dir.glob(pattern).each do |path|
        next if File.directory?(path)
        
        begin
          content = File.read(path)
          if content =~ regex
            # Calculate path relative to the requested search directory
            relative_path = Pathname.new(path).relative_path_from(Pathname.new(target_dir)).to_s
            matching_files << relative_path
          end
        rescue => e
          # Skip files that cannot be read (e.g. permission issues)
          next
        end
      end
    rescue => e
      return render json: { error: "Internal server error during file search: #{e.message}" }, status: :internal_server_error
    end

    render json: { files: matching_files }, status: :ok
  end
end