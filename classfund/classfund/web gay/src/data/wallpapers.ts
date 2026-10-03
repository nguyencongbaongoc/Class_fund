export interface WallpaperItem {
  id: string;
  name: string;
  url: string;
  category: 'abstract' | 'landscape' | 'beauty';
  isSecret?: boolean;
}

export const WALLPAPER_CATEGORIES = [
  { id: 'abstract', label: 'Trừu Tượng & Tối Giản' },
  { id: 'landscape', label: 'Phong Cảnh' },
  { id: 'beauty', label: 'Phái Đẹp' },
] as const;

export const WALLPAPERS: WallpaperItem[] = [
  // Danh mục: Trừu Tượng & Tối Giản
  {
    id: 'wp-1',
    name: 'Vũ Điệu Hoàng Kim',
    url: 'https://phongvu.vn/cong-nghe/wp-content/uploads/2025/12/hinh-nen-macbook-55-1.jpg',
    category: 'abstract',
  },
  {
    id: 'wp-2',
    name: 'Dải Lụa Hồng Quý Tộc',
    url: 'https://phongvu.vn/cong-nghe/wp-content/uploads/2025/12/hinh-nen-macbook-47-1.jpg',
    category: 'abstract',
  },
  {
    id: 'wp-3',
    name: 'Dòng Chảy Huyết Ngọc',
    url: 'https://phongvu.vn/cong-nghe/wp-content/uploads/2025/12/hinh-nen-macbook-52-1.jpg',
    category: 'abstract',
  },
  {
    id: 'wp-4',
    name: 'Cực Quang Lam Ngọc Thượng Lưu',
    url: 'https://phongvu.vn/cong-nghe/wp-content/uploads/2025/12/hinh-nen-macbook-56-1.jpg',
    category: 'abstract',
  },
  {
    id: 'wp-5',
    name: 'Bình Minh Tối Giản',
    url: 'https://phongvu.vn/cong-nghe/wp-content/uploads/2025/12/hinh-nen-macbook-61-1.jpg',
    category: 'abstract',
  },
  {
    id: 'wp-ab-new',
    name: 'Pha Lê Ngũ Sắc Ánh Kim',
    url: 'https://i.ibb.co/s8zK5ky/iridescent-glass-3840x2160-25854.jpg',
    category: 'abstract',
  },

  // Danh mục: Phong Cảnh
  {
    id: 'wp-6',
    name: 'Hoàng Hôn Đỉnh Sơn Huyền Bí',
    url: 'https://server.wallpaperalchemy.com/storage/wallpapers/4438/macos-sierra-wallpaper-alpine-sunset-mountain-peak.jpg',
    category: 'landscape',
  },
  {
    id: 'wp-7',
    name: 'Vạn Dặm Giang Sơn Hoàng Kim',
    url: 'https://i.ibb.co/99X3Kp6F/big-sur-mountains-golden-hour-sunset-evening-macos-big-sur-3840x2160-1499.jpg',
    category: 'landscape',
  },
  {
    id: 'wp-8',
    name: 'Sương Mù Thu Lãnh Ngàn Năm',
    url: 'https://i.ibb.co/qYDjmJDt/macos-high-sierra-mountains-stock-landscape-foggy-autumn-3840x2160-4037.jpg',
    category: 'landscape',
  },
  {
    id: 'wp-9',
    name: 'Vách Đá Hoa Cương Uy Nghiêm',
    url: 'https://i.ibb.co/jvjdYgLx/el-capitan-yosemite-national-park-mountains-os-x-el-capitan-3840x2160-4010.jpg',
    category: 'landscape',
  },
  {
    id: 'wp-10',
    name: 'Đại Ngàn Trầm Mặc Tinh Khôi',
    url: 'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?fm=jpg&q=60&w=3000&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NHx8bGFuZHNjYXBlJTIwd2FsbHBhcGVyfGVufDB8fDB8fHww',
    category: 'landscape',
  },
  {
    id: 'wp-ls-new',
    name: 'Băng Tuyết Kỳ Vĩ Trùng Điệp',
    url: 'https://i.ibb.co/TMrfQTkF/snow-mountains-3840x2160-26362.jpg',
    category: 'landscape',
  },

  // Danh mục: Phái Đẹp
  {
    id: 'wp-11',
    name: 'Nàng Thơ Đài Các Ánh Dương',
    url: 'https://i.ibb.co/Qt0QdV8/le-sserafim-made-my-3840x2160-27214.jpg',
    category: 'beauty',
  },
  {
    id: 'wp-12',
    name: 'Mỹ Nhân Tử Đằng Kiêu Kỳ',
    url: 'https://i.ibb.co/gLNt6sWL/jennie-purple-3840x2160-26909.jpg',
    category: 'beauty',
  },
  {
    id: 'wp-13',
    name: 'Nét Đẹp Thuần Khiết Nắng Mai',
    url: 'https://cdn2.tuoitre.vn/471584752817336320/2024/3/27/img8976-1711535116828953465649.jpeg',
    category: 'beauty',
  },
  {
    id: 'wp-14',
    name: 'Thần Thái Quyền Quý Sang Trọng',
    url: 'https://i.ibb.co/mfH704n/aespa-dirty-work-5k-23776.jpg',
    category: 'beauty',
  },
  {
    id: 'wp-15',
    name: 'Tuyệt Sắc Giai Nhân Ánh Dạ',
    url: 'https://i.ibb.co/H0HPn1P/women-model-cosplay-indoors-women-indoors-hd-wallpaper-036fa747ded2a744c6eada64746d7f7a.jpg',
    category: 'beauty',
    isSecret: true,
  },
  {
    id: 'wp-16',
    name: 'Tiểu Thư Quý Tộc Thời Thượng',
    url: 'https://upload.wikimedia.org/wikipedia/commons/7/7b/Babymonster_at_Incheon_Airport.jpg?utm_source=vi.wikipedia.org&utm_campaign=index&utm_content=original',
    category: 'beauty',
  },
];
