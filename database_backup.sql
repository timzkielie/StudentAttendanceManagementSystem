-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Oct 29, 2026 at 12:09 PM
-- Server version: 10.11.16-MariaDB
-- PHP Version: 8.3.36

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `attendance_system`
--

-- --------------------------------------------------------

--
-- Table structure for table `attendance`
--

CREATE TABLE `attendance` (
  `id` int(11) NOT NULL,
  `student_id` varchar(191) NOT NULL,
  `status` varchar(10) NOT NULL,
  `attendance_date` date NOT NULL,
  `attendance_time` time NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `attendance`
--

INSERT INTO `attendance` (`id`, `student_id`, `status`, `attendance_date`, `attendance_time`) VALUES
(1, '941689', 'PRESENT', '2026-10-24', '22:57:52'),
(2, '549866', 'ABSENT', '2026-10-24', '22:57:52'),
(5, '8765138', 'PRESENT', '2026-10-24', '22:57:21'),
(6, '82157451', 'PRESENT', '2026-10-24', '22:57:21'),
(9, '8765138', 'PRESENT', '2026-10-25', '17:48:14'),
(10, '82157451', 'ABSENT', '2026-10-25', '17:48:14'),
(13, '941689', 'ABSENT', '2026-10-25', '17:51:43'),
(14, '549866', 'PRESENT', '2026-10-25', '17:51:43'),
(19, '941689', 'PRESENT', '2026-10-28', '21:26:07'),
(20, '549866', 'PRESENT', '2026-10-28', '19:26:37'),
(22, '8765138', 'PRESENT', '2026-10-28', '19:26:47'),
(23, '82157451', 'PRESENT', '2026-10-28', '19:26:47');

-- --------------------------------------------------------

--
-- Table structure for table `students`
--

CREATE TABLE `students` (
  `student_id` varchar(191) NOT NULL,
  `fullname` varchar(255) NOT NULL,
  `section` varchar(255) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `course` varchar(255) NOT NULL DEFAULT 'Unassigned'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `students`
--

INSERT INTO `students` (`student_id`, `fullname`, `section`, `user_id`, `course`) VALUES
('549866', 'PEREZ, RICA MAE M.', 'SILVER', 1, 'BSIT'),
('82157451', 'SMITH, CATHALYNE B.', 'OPAL', 1, 'HRM'),
('8765138', 'PEREZ, TIMOTHY A.', 'OPAL', 1, 'HRM'),
('941689', 'ALVAREZ, MICO L.', 'DIAMOND', 1, 'BSIT');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(191) NOT NULL,
  `password` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `username`, `password`) VALUES
(1, 'CRIZTINE', 'pbkdf2_sha256$310000$11c89fe5976162a058ee6e5f26b95f5f$b5426170b6e777bdeef6e6853e606b365f9673c453ade0d4b221aacdd7f9202f');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `attendance`
--
ALTER TABLE `attendance`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_attendance_student_date` (`student_id`,`attendance_date`);

--
-- Indexes for table `students`
--
ALTER TABLE `students`
  ADD PRIMARY KEY (`student_id`),
  ADD KEY `idx_students_class` (`course`,`section`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `attendance`
--
ALTER TABLE `attendance`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=26;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `attendance`
--
ALTER TABLE `attendance`
  ADD CONSTRAINT `fk_attendance_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
